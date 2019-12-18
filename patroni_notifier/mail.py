import boto3
from botocore.exceptions import ClientError
from jinja2 import Environment, PackageLoader, select_autoescape
import consul
from patroni_notifier import click
import datetime
import base64
import ast
import humanize
import socket
import dateutil.parser
import mimetypes
from email.message import EmailMessage
from email.utils import make_msgid


class Mailer:
    def __init__(self, config, metastore, cluster_name):

        self.cluster_members = [{}]
        self.cluster_name = cluster_name
        self.host = socket.gethostbyname(socket.gethostname())
        self.config = config

        self.config["logo_b64"] = self.encode_image(self.config["logo"])

        if metastore != "consul":
            raise NotImplementedError
        else:
            self.consul_client = consul.Consul()

        self.charset = "UTF-8"
        self.aws_region = "us-east-1"
        self.client = boto3.client("ses", region_name=self.aws_region)
        self.jinja_env = Environment(
            loader=PackageLoader("patroni_notifier", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.template_html = self.jinja_env.get_template("event.html.j2")
        self.template_txt = self.jinja_env.get_template("simple.txt")
        # self.config_set = 'ConfigSet'

    def encode_image(self, filename):
        encoded = base64.b64encode(open(filename, "rb").read()).decode("utf-8")

        return encoded

    def get_history(self):
        history = self.consul_client.kv.get(f"service/{self.cluster_name}/history")
        history = ast.literal_eval(history[1]["Value"].decode("utf-8"))

        for obj in history:
            obj[1] = humanize.naturalsize(obj[1])
            if len(obj) > 3:
                obj[3] = dateutil.parser.parse(obj[3]).strftime(
                    "%-m/%d/%Y %-I:%M %p %Z"
                )

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

    def send_email(self, action, role):
        self.get_cluster_info()

        msg = EmailMessage()

        msg["From"] = self.config["email_sender"]
        msg["To"] = self.config["email_recipient"]
        msg["Subject"] = f"{action.upper()} event - {role}@{self.host}"

        time = datetime.datetime.now().strftime("%-m/%d/%Y %-I:%M %p")

        msg.set_content(self.template_txt.render())

        image_cid = make_msgid(domain="ptbnl.io")
        msg.add_alternative(
            self.template_html.render(
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
                logo_cid=image_cid[1:-1],
            ),
            subtype="html",
        )

        with open(self.config["logo"], "rb") as img:
            maintype, subtype = mimetypes.guess_type(img.name)[0].split("/")
            msg.get_payload()[1].add_related(
                img.read(), maintype=maintype, subtype=subtype, cid=image_cid
            )

        try:
            response = self.client.send_raw_email(
                Source=self.config["email_sender"],
                Destinations=[self.config["email_recipient"],],
                RawMessage={"Data": msg.as_string(),},
            )

        except ClientError as e:
            click.echo(e.response["Error"]["Message"])
        else:
            msg_id = response["MessageId"]
            click.echo(f"Email sent! Message ID: { msg_id }")
