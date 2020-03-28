import boto3
from botocore.exceptions import ClientError
from jinja2 import Environment, PackageLoader, select_autoescape
import consul
from patroni_notifier import click
import datetime
import pytz
import base64
import ast
import humanize
import socket
import dateutil.parser
import mimetypes
import requests
from urllib.parse import urlparse
from email.message import EmailMessage
from email.utils import make_msgid
from haproxystats import HAProxyServer


class Mailer:
    def __init__(self, config, metastore, cluster_name):

        self.cluster_members = [{}]
        self.cluster_name = cluster_name
        self.host = socket.gethostbyname(socket.gethostname())
        self.config = config

        self.external_link_icon = """iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAA
            ACNMs+9AAAAQElEQVR42qXKwQkAIAxDUUdxtO6/RBQkQZvSi8I/pL4BoGw/XPk
            h4XigPmsUgh0626AjRsgxHTkUThsG2T/sIlzdTsp52kSS1wAAAABJRU5ErkJgg
            g=="""

        self.logo = self.get_image(self.config["logo_url"])
        self.logo_b64 = self.encode_image(self.logo)

        if metastore != "consul":
            raise NotImplementedError
        else:
            self.consul_client = consul.Consul()

        self.haproxy = HAProxyServer(self.config["haproxy"]["address"])

        self.charset = "UTF-8"
        self.aws_region = "us-east-1"
        self.client = boto3.client("ses", region_name=self.aws_region)

        self.jinja_env = Environment(
            loader=PackageLoader("patroni_notifier", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.jinja_env.filters["naturalsize"] = humanize.naturalsize
        self.jinja_env.filters["naturaltime"] = humanize.naturaldelta

        self.template_html = self.jinja_env.get_template("event.html.j2")
        self.template_txt = self.jinja_env.get_template("simple.txt")

    def get_image(self, filename):

        if self.is_url(filename):
            obj = requests.get(filename).content
        else:
            obj = open(filename, "rb").read()

        return obj

    def encode_image(self, obj):
        return base64.b64encode(obj)

    def is_url(self, url):
        return urlparse(url).scheme != ""

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

    def get_load_balancer_info(self):

        final = []
        # next(obj in obj_list if predicate(obj))
        for frontend, backend in self.config["haproxy"]["load_balancers"].items():

            for fe in self.haproxy.frontends:
                if fe.name == frontend:
                    for be in self.haproxy.backends:
                        if be.name == backend:
                            final.append({"frontend": fe, "backends": be.listeners})

        return final

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
                try:

                    member["delay"] = humanize.naturalsize(
                        member["xlog_location"] - optime
                    )

                except KeyError:
                    member["delay"] = "N/A"

            db_sys_id = self.consul_client.kv.get(
                f"service/{self.cluster_name}/initialize"
            )
            self.database_id = ast.literal_eval(db_sys_id[1]["Value"].decode("utf-8"))
            self.get_history()

        except Exception as e:
            click.echo(f"Error generating consul report: { e }")
            self.cluster_members = []
            self.database_id = ""

    def construct_message(self, action, role):

        msg = EmailMessage()

        msg["From"] = self.config["email_sender"]
        msg["To"] = self.config["email_recipient"]
        msg["Subject"] = f"{action.upper()} event - {role}@{self.host}"

        time = datetime.datetime.now(pytz.timezone("US/Central")).strftime(
            "%-m/%d/%Y %-I:%M %p %Z"
        )

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
                load_balancers=self.load_balancers,
            ),
            subtype="html",
        )

        # add the image to the email via a mimetype multipart upload
        # there needs to be coordination between content-id's embedded
        # in html, and the cid of the attached file

        maintype, subtype = mimetypes.guess_type(self.config["logo_url"])[0].split("/")
        msg.get_payload()[1].add_related(
            self.logo, maintype=maintype, subtype=subtype, cid=image_cid
        )

        return msg

    def send_email(self, action, role):
        self.get_cluster_info()
        self.load_balancers = self.get_load_balancer_info()

        msg = self.construct_message(action, role)

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
