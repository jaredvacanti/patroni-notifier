import boto3
from botocore.exceptions import ClientError
from jinja2 import Environment, PackageLoader, select_autoescape
import consul
import click
import yaml
import datetime


class Mailer:
    def __init__(self, config, metastore_addr):
        self.charset = "UTF-8"
        self.aws_region = "us-east-1"
        self.consul_client = consul.Consul()
        self.client = boto3.client("ses", region_name=self.aws_region)
        self.jinja_env = Environment(
            loader=PackageLoader("patroni_notifier", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.template_html = self.jinja_env.get_template("simple.html")
        self.template_txt = self.jinja_env.get_template("simple.txt")
        self.consul_data = {}
        # self.config_set = 'ConfigSet'

        with open(config, "r") as stream:
            try:
                self.config = yaml.safe_load(stream)

            except yaml.YAMLError as exc:
                click.echo(exc)

    def get_consul_data(self):
        try:
            self.consul_data = self.consul_client.kv.get("services/pg-cluster")
        except Exception:
            self.consul_data = {"error": "Not able to query consul"}

    # sender, subject,
    def send_email(self, action, role, cluster_name):
        self.get_consul_data()

        try:
            response = self.client.send_email(
                Destination={"ToAddresses": [self.config["email_recipient"],],},
                Message={
                    "Body": {
                        "Html": {
                            "Charset": self.charset,
                            "Data": self.template_html.render(
                                consul_data=self.consul_data,
                                servers=[],
                                cluster_name=cluster_name,
                                action=action,
                                role=role,
                                time=datetime.datetime.now(),
                                dashboard_url=self.config["dashboard_url"],
                            ),
                        },
                        "Text": {
                            "Charset": self.charset,
                            "Data": self.template_txt.render(),
                        },
                    },
                    "Subject": {
                        "Charset": self.charset,
                        "Data": self.config["email_subject"],
                    },
                },
                Source=self.config["email_sender"],
                # ConfigurationSetName=self.config_set,
            )
        except ClientError as e:
            click.echo(e.response["Error"]["Message"])
        else:
            msg_id = response["MessageId"]
            click.echo(f"Email sent! Message ID: { msg_id }")
