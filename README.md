# `configure_aep`

`configure_aep` is used to configure a MultiTech Conduit with AEP firmware that is in commissioning mode. It configures the Conduit for use with the IthacaThings administration system by Jeff Honig.

<!-- TOC depthfrom:2 updateonsave:true -->

- [Introduction](#introduction)
- [Running from a virtual environment](#running-from-a-virtual-environment)

<!-- /TOC -->

## Introduction

The steps in the process are as follows.

## Running from a virtual environment

```bash
# after cloning
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

python3 -m commission_aep --help
```
