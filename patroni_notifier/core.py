import click
from patroni_notifier.mail import Mailer


@click.command("patroni-notify", short_help="Send notification of a Patroni Event.")
@click.argument("action")
@click.argument("role")
@click.argument("cluster-name")
@click.option(
    "--config",
    default="/config/patroni.yml",
    help="The patroni configuration to read from.",
)
@click.option(
    "--metastore-addr",
    default="consul",
    help="The patroni configuration to read from.",
)
def patroni_notify(action, role, cluster_name, config, metastore_addr):
    """Query the metastore for relevant Patroni information and send notification"""

    mailer = Mailer(config, metastore_addr, cluster_name)

    # current actions supported:
    # patroni events (on_start, on_stop, on_reload, on_restart, on_role_change)
    # bootstrap, backup
    mailer.send_email(action, role)
