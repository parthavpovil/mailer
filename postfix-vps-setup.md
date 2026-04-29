# Postfix VPS Setup — SES SMTP Relay

Server: `srv1501537` (Hostinger VPS)
Region: `eu-north-1` (Stockholm)
Domain: `newsletter.booknitive.com`
Date: 2026-04-23

---

## What This Does

Postfix runs as a system daemon on the VPS. The Python app sends mail to `localhost:25`, and Postfix relays it to Amazon SES. The app never talks to SES directly.

```
Python app → localhost:25 → Postfix → SES (eu-north-1) → recipient
```

---

## What Was Done

### 1. Installed Postfix

```bash
sudo apt update && sudo apt install -y postfix libsasl2-modules mailutils bsd-mailx
# Selected "Internet Site" during install
```

### 2. Wrote `/etc/postfix/main.cf`

```ini
myhostname = newsletter.booknitive.com
myorigin = /etc/mailname
mydestination = localhost
relayhost = [email-smtp.eu-north-1.amazonaws.com]:587

smtp_sasl_auth_enable = yes
smtp_sasl_security_options = noanonymous
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_use_tls = yes
smtp_tls_security_level = encrypt
smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt

inet_interfaces = loopback-only
```

### 3. Wrote `/etc/postfix/sasl_passwd`

```
[email-smtp.eu-north-1.amazonaws.com]:587 <SMTP_USERNAME>:<SMTP_PASSWORD>
```

> Credentials are IAM-generated SES SMTP credentials (not AWS root credentials).
> The actual values are stored only on the VPS. Do not put them in `.env` or code.

### 4. Secured and Applied

```bash
sudo chmod 600 /etc/postfix/sasl_passwd
sudo postmap /etc/postfix/sasl_passwd
sudo systemctl restart postfix
sudo systemctl enable postfix
```

### 5. Verified It Works

Sent a test email:
```bash
echo "Subject: SES Test
From: no-reply@newsletter.booknitive.com
To: support@booknitive.com

Test" | sendmail -f no-reply@newsletter.booknitive.com support@booknitive.com
```

Log confirmed delivery:
```
status=sent (250 Ok 0110019db918895c-...)
```

---

## Useful Commands

| Task | Command |
|---|---|
| Check Postfix status | `sudo postfix status` |
| View mail queue | `sudo mailq` |
| View logs | `sudo grep postfix /var/log/syslog \| tail -30` |
| Restart Postfix | `sudo systemctl restart postfix` |
| Test send | `echo "Subject: Test\n\nBody" \| sendmail -f no-reply@newsletter.booknitive.com you@example.com` |

---

## DNS Records Added (Cloudflare / domain DNS)

| Type | Name | Value |
|---|---|---|
| CNAME | `4bvpnlmgaieekwpyubisaozq7zqfd4sb._domainkey.newsletter.booknitive.com` | `4bvpnlmgaieekwpyubisaozq7zqfd4sb.dkim.amazonses.com` |
| CNAME | `euydqmgbfcqmhiqk7rpglxjnnxwnokml._domainkey.newsletter.booknitive.com` | `euydqmgbfcqmhiqk7rpglxjnnxwnokml.dkim.amazonses.com` |
| CNAME | `7w4ona2gzrbyxy375cvy3wolo7rnyp4k._domainkey.newsletter.booknitive.com` | `7w4ona2gzrbyxy375cvy3wolo7rnyp4k.dkim.amazonses.com` |
| TXT | `newsletter.booknitive.com` | `v=spf1 include:amazonses.com ~all` |

---

## AWS SES Status

| Item | Status |
|---|---|
| Domain `newsletter.booknitive.com` | Verified |
| DKIM | Verified |
| SMTP credentials | Created (IAM user: `ses-smtp-user.20260423-102245`) |
| Production access | Requested — pending AWS approval (24h) |

---

## What's Still Pending

- [ ] AWS approves production access (sandbox → production)
- [ ] SNS topic setup for bounce/complaint webhooks
- [ ] ARQ worker systemd service on VPS
- [ ] Wire `queue_*` calls into existing app routers
