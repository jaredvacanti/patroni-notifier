# Patroni Notifier

![](https://github.com/jaredvacanti/patroni-notifier/workflows/Publish%20to%20PyPI/badge.svg)
![PyPI](https://img.shields.io/pypi/v/patroni-notifier?style=flat-square)
![PyPI - License](https://img.shields.io/pypi/l/patroni-notifier?style=flat-square)

This is a simple command line program to send templated emails from AWS SES in response
to Patroni database events.

## Supported Actions

action | description
--- | ---
reload | reconfigure a running database 
restart | `-HUP` sent to main process
role_change | promotions from replica to master
start | start postgresql process
stop | stop/pause postgresql process
backup | backup and upload to s3 



# Quick Start

### Installation

```
pip install patroni-notifier
```

Currently emails are sent using Amazon SES. Authenication can use IAM roles
or you can place a `aws.env` in your home directory with credentials.


```
Usage: patroni-notify <action> <role> <cluster_name> [OPTIONS]

  Query the metastore for relevant Patroni information and send notification

Arguments:
  action: <action>  The action.  [required]

[OPTIONS]:
  --config-file PATH      The path to the configuration file.  [default:
                          /etc/patroni.yml]
  --metastore TEXT        The DCS address.  [default: consul]
  --logo-url TEXT         The logo url.
  --logo PATH             The logo to be base64 encoded and embedded.
  --email-sender TEXT     The email address to send notifications from.
  --email-recipient TEXT  The email address to recieve notifications.
  --haproxy-addr TEXT     The HAProxy TCP load-balancer address.
  -h, --help              Show this message and exit.
```

### Configuration

System-wide configurations are done in the `patroni.yml` file required for 
Patroni operations. You can further specify a config file location using 
`--config` as a command line option, which defaults to `/config/patroni.yml`.


**Required Settings** in patroni.yml:

```
postgresql:
  callbacks:
    on_reload: /usr/local/bin/patroni-notify
    on_restart: /usr/local/bin/patroni-notify
    on_role_change: /usr/local/bin/patroni-notify
    on_start: /usr/local/bin/patroni-notify
    on_stop: /usr/local/bin/patroni-notify

patroni_notifier:
  email_sender: John Doe <example.com>
  email_recipient: test@example.com
  email_subject: Sample Subject
  dashboard_url: http://example.com/dashboard/
  logo_url: example-url
  logo_link_url: http://www.example.com
  haproxy:
    address: 10.0.1.139:9001
    load_balancers:
      master_postgresql: backend_master
      replicas_postgresql: backend_replicas
```

Patroni invokes callback scripts to run on certain database events. 
Patroni will pass the action, role and cluster name. Internally,
`patroni-notifier` will parse the action to determine what html template
to use.


# Development

In order to access the Distributed Configuration Storage (DCS), the S3
backups, and the access rights to send test emails from SES, the test
environment needs to run on an EC2 instance or be provided with the correct
roles.

- VSCode SSH Remote Login
- `git clone https://github.com/jaredvacanti/patroni-notifier.git`
- `cd patroni-notifier`
- `sudo apt-get install python3-venv`
- `python3 -m venv .venv`
- `. .venv/bin/activate`
- `pip install --upgrade pip`
- `pip install poetry`
- `poetry install`
- Install Remote Python Debugger (VSCode Extension)


## Tests

```
poetry run tox
```

## License

MIT License

Copyright (c) 2019-2020

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
