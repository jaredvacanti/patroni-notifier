import os
import socket
import subprocess
import socket
import requests

import click
import requests
import consul
from patroni_notifier.mail import Mail

c = consul.Consul()

data = c.kv.get("services/pg-cluster")


@click.command("patroni-notify", short_help="Send notification of a Patroni Event.")
@click.pass_context
@click.option(
    "--config", default="patroni.yml", help="The patroni configuration to read from.",
)
def patroni_notify(metastore_addr):
    """Query the metastore for relevant Patroni information and send notification"""

    click.echo(metastore_addr)

