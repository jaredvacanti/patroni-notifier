from patroni_notifier import click
from patroni_notifier.mail import Mailer
from patroni_notifier.config import CommandWithConfigFileHelper
import yaml


@click.command(
    "patroni-notify",
    short_help="Send notification of a Patroni Event.",
    cls=CommandWithConfigFileHelper("config_file"),
)
@click.argument("action", help="The action.")
@click.argument("role")
@click.argument("cluster-name")
@click.option(
    "--config-file",
    type=click.Path(),
    default="/etc/patroni.yml",
    help="The path to the configuration file.",
    show_default=True,
)
@click.option(
    "--metastore", default="consul", show_default=True, help="The DCS address.",
)
@click.option(
    "--logo-url", show_default=True, help="The logo url.",
)
@click.option(
    "--logo", type=click.Path(), help="The logo to be base64 encoded and embedded.",
)
@click.option(
    "--email-sender",
    type=click.STRING,
    help="The email address to send notifications from.",
    show_default=True,
)
@click.option(
    "--email-recipient",
    type=click.STRING,
    help="The email address to recieve notifications.",
    show_default=True,
)
@click.option(
    "--haproxy-addr", show_default=True, help="The HAProxy TCP load-balancer address.",
)
def patroni_notify(
    action,
    role,
    cluster_name,
    config_file,
    metastore,
    logo_url,
    logo,
    email_sender,
    email_recipient,
    haproxy_addr,
):
    """
    Query the metastore for relevant Patroni information and send notification
    """

    with open(config_file, "r") as stream:
        try:
            patroni_config = yaml.safe_load(stream)
            config = patroni_config["patroni_notifier"]

        except yaml.YAMLError as exc:
            click.echo(exc)

    if logo:
        config["logo"] = logo

    if logo_url:
        config["logo_url"] = logo_url

    if email_sender:
        config["email_sender"] = email_sender

    if email_recipient:
        config["email_recipient"] = email_recipient

    mailer = Mailer(config, metastore, cluster_name)

    # current actions supported:
    # patroni events (on_start, on_stop, on_reload, on_restart, on_role_change)
    # bootstrap, backup
    mailer.send_email(action, role)
