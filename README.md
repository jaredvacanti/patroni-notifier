# Patroni Notifier

![](https://github.com/jaredvacanti/patroni-notifier/workflows/Publish%20to%20PyPI/badge.svg)
![PyPI](https://img.shields.io/pypi/v/patroni-notifier?style=flat-square)
![PyPI - License](https://img.shields.io/pypi/l/patroni-notifier?style=flat-square)

This is a simple command line program to send templated emails from AWS SES in response
to Patroni database events.

## Installation

```
pip install patroni-notifier
```

## Usage

System-wide configurations are done in the `patroni.yml` file required for 
Patroni operations. You can further specify a config file location using 
`--config` as a command line option, which defaults to `/config/patroni.yml`.

**Required Settings in patroni.yml**
```
email_sender: John Doe <example.com>
email_recipient: test@example.com
email_subject: Sample Subject
```

Patroni will send a notification on role change by invoking callback scripts 
to run on certain actions. Patroni will pass the action, role and cluster name.

The program is then run like `patroni-notify ACTION ROLE CLUSTER_NAME`. Add this
snippet to your `patroni.yml`:

```
callbacks:
  on_reload: /usr/local/bin/patroni-notify
  on_restart: /usr/local/bin/patroni-notify
  on_role_change: /usr/local/bin/patroni-notify
  on_start: /usr/local/bin/patroni-notify
  on_stop: /usr/local/bin/patroni-notify
```
### Authentication

Currently emails are sent using Amazon SES. Authenication can use IAM roles
or you can place a `aws.env` in your home directory with credentials.

## Tests

```
poetry run tox
```

## License

MIT License

Copyright (c) 2019

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
