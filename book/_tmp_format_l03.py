from pathlib import Path
import re

se340 = Path(r"book/SE/SE340-cloud-and-delivery/SE340-L03-cloud-infrastructure-and-aws-architecture.md")
cs340 = Path(r"book/CS/CS340-data-systems-beyond-relational/CS340-L03-document-databases-and-mongodb.md")

cs = cs340.read_text(encoding="utf-8")
start = cs.index("# Part I — Intuition")
end = cs.index("*The intuition pass ends here.*") + len("*The intuition pass ends here.*")
raw_block = cs[start:end]
section1 = cs.index("# 1. The Hotel Document That Ate the Database")
deep_dive = cs[section1:]

cs_front = """---
id: CS340-L03
course: CS340
title: "Document Databases and MongoDB"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS340-L02
next: CS340-L04
---

# CS340 — Data Systems Beyond Relational Databases

## Lecture 03: Document Databases and MongoDB

*Why putting related information together can transform an application's performance, why some documents become architectural disasters, and how MongoDB turns data modeling into a question of ownership, atomicity, and change.*

---

"""
cs340.write_text(cs_front + deep_dive, encoding="utf-8")
print("CS340-L03 restored; length", len(cs_front + deep_dive))

body = raw_block[len("# Part I — Intuition") :].lstrip("\n")
body = re.sub(r"^## (.+)$", r"### \1", body, flags=re.M)
body = body.replace("### What is a security group?", "#### What is a security group?")
body = body.replace(
    "### Three questions before the Deep Dive",
    "#### Three questions before the Deep Dive",
)

old_q = """#### Three questions before the Deep Dive

**First:** You're running an API in ECS with Fargate, and PostgreSQL becomes overloaded. Is AWS responsible for fixing the application's database query patterns?

No. Fargate manages underlying container execution infrastructure, but application behavior and database workload design remain engineering responsibilities.

**Second:** Your application runs on a private-subnet container and must access a database. Does it necessarily need a public IP address?

No. Appropriate VPC networking and security rules can allow private communication.

**Third:** You have an S3 bucket containing private invoices. Does granting your backend an IAM role automatically ensure customers can access only their own invoices?

No. IAM controls the workload's AWS permissions. The application must still enforce customer-level authorization."""

new_q = """#### Three questions before the Deep Dive

1. You're running an API in ECS with Fargate, and PostgreSQL becomes overloaded. Is AWS responsible for fixing the application's database query patterns? **No. Fargate manages underlying container execution infrastructure, but application behavior and database workload design remain engineering responsibilities.**
2. Your application runs on a private-subnet container and must access a database. Does it necessarily need a public IP address? **No. Appropriate VPC networking and security rules can allow private communication.**
3. You have an S3 bucket containing private invoices. Does granting your backend an IAM role automatically ensure customers can access only their own invoices? **No. IAM controls the workload's AWS permissions. The application must still enforce customer-level authorization.**"""

if old_q not in body:
    raise SystemExit("three questions block not found")
body = body.replace(old_q, new_q)
body = re.sub(r'```text id="[^"]+"', "```text", body)

needle = (
    "**Think of AWS as a collection of building blocks for operating an application, "
    "with different degrees of responsibility delegated to the cloud provider.**\n\n"
    "Let's build one small production system and discover where the pieces fit.\n\n"
    "### 1. EC2"
)
repl = (
    "**Think of AWS as a collection of building blocks for operating an application, "
    "with different degrees of responsibility delegated to the cloud provider.**\n\n"
    "Let's build one small production system and discover where the pieces fit.\n\n"
    "---\n\n"
    "### 1. EC2"
)
if needle not in body:
    raise SystemExit("picture/section1 join not found")
body = body.replace(needle, repl, 1)

if body.rstrip().endswith("*The intuition pass ends here.*"):
    body = body.rstrip()[: -len("*The intuition pass ends here.*")].rstrip() + "\n"

framing = """# Part I — Intuition

*A hotel-booking app that works on your laptop still needs compute, storage, networking, identity, and observability before customers can use it. AWS is a set of building blocks for those jobs — not a catalogue of unrelated product names.*

This pass builds one mental picture. Part II develops the same picture with full technical depth.

"""

part_i = framing + body + "\n*The intuition pass ends here.*\n\n---\n\n# Part II — Deep Dive\n\n"

se = se340.read_text(encoding="utf-8")
marker = "## 1. The Serverless Application That Scaled Itself to Death"
idx = se.index(marker)
blurb_end = se.index(
    "*How the cloud made computing resources elastic, infrastructure programmable, and architectural mistakes spectacularly scalable.*"
)
after_blurb = se.index("\n---\n", blurb_end) + len("\n---\n")
new_se = se[:after_blurb] + "\n" + part_i + se[idx:]
se340.write_text(new_se, encoding="utf-8")
print("SE340-L03 updated; length", len(new_se))
print("Part I at", new_se.index("# Part I — Intuition"))
print("Part II at", new_se.index("# Part II — Deep Dive"))
