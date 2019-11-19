import boto3
from botocore.exceptions import ClientError
from jinja2 import Environment, PackageLoader, select_autoescape
import consul
import click
import yaml
import datetime
import ast
import humanize
import socket

# ast.literal_eval(b"{'one': 1, 'two': 2}")


class Mailer:
    def __init__(self, config, metastore_addr, cluster_name):
        self.charset = "UTF-8"
        self.aws_region = "us-east-1"
        self.consul_client = consul.Consul()
        self.client = boto3.client("ses", region_name=self.aws_region)
        self.jinja_env = Environment(
            loader=PackageLoader("patroni_notifier", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.template_html = self.jinja_env.get_template("event.html.j2")
        self.template_txt = self.jinja_env.get_template("simple.txt")
        self.cluster_members = [{}]
        self.cluster_name = cluster_name
        self.host = socket.gethostbyname(socket.gethostname())
        # self.config_set = 'ConfigSet'

        with open(config, "r") as stream:
            try:
                patroni_config = yaml.safe_load(stream)
                self.config = patroni_config["patroni_notifier"]

            except yaml.YAMLError as exc:
                click.echo(exc)

    def get_history(self):
        history = self.consul_client.kv.get(f"service/{self.cluster_name}/history")
        history = ast.literal_eval(history[1]["Value"].decode("utf-8"))

        for obj in history:
            obj[1] = humanize.naturalsize(obj[1])

        self.history = history

    def get_cluster_info(self):
        try:
            consul_members = self.consul_client.kv.get(
                f"service/{self.cluster_name}/members", recurse=True
            )

            self.cluster_members = [
                {
                    **ast.literal_eval(member["Value"].decode("utf-8")),
                    **{"hostname": member["Key"].split("/")[-1]},
                }
                for member in consul_members[1]
            ]
            optime_resp = self.consul_client.kv.get(
                f"service/{self.cluster_name}/optime/leader"
            )
            optime = int(optime_resp[1]["Value"].decode("utf-8"))
            self.optime_fmtd = humanize.naturalsize(optime)

            for member in self.cluster_members:
                member["delay"] = humanize.naturalsize(member["xlog_location"] - optime)

            db_sys_id = self.consul_client.kv.get(
                f"service/{self.cluster_name}/initialize"
            )
            self.database_id = ast.literal_eval(db_sys_id[1]["Value"].decode("utf-8"))
            self.get_history()

        except Exception:
            self.cluster_members = []
            self.database_id = ""

    # sender, subject,
    def send_email(self, action, role):
        self.get_cluster_info()

        time = datetime.datetime.now().strftime("%-m/%d/%Y %-I:%M %p")
        subject = f"{action.upper()} event - {role}@{self.host}"

        try:
            response = self.client.send_email(
                Destination={"ToAddresses": [self.config["email_recipient"],],},
                Message={
                    "Body": {
                        "Html": {
                            "Charset": self.charset,
                            "Data": self.template_html.render(
                                cluster_members=self.cluster_members,
                                cluster_name=self.cluster_name,
                                history=self.history,
                                action=action,
                                role=role,
                                time=time,
                                host=self.host,
                                optime=self.optime_fmtd,
                                database_id=self.database_id,
                                dashboard_url=self.config["dashboard_url"],
                                logo_url=self.config["logo_url"],
                            ),
                        },
                        "Text": {
                            "Charset": self.charset,
                            "Data": self.template_txt.render(),
                        },
                    },
                    "Subject": {"Charset": self.charset, "Data": subject,},
                },
                Source=self.config["email_sender"],
                # ConfigurationSetName=self.config_set,
            )
        except ClientError as e:
            click.echo(e.response["Error"]["Message"])
        else:
            msg_id = response["MessageId"]
            click.echo(f"Email sent! Message ID: { msg_id }")
