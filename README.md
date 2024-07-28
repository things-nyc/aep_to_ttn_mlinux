# `aep_to_ttn_mlinux`

`aep_to_ttn_mlinux` is used to configure a MultiTech Conduit with AEP firmware that is in commissioning mode. It configures the Conduit for use with the [IthacaThings administration system](https://github.com/IthacaThings/ttn-multitech-cm) by Jeff Honig.

<!-- TOC depthfrom:2 updateonsave:true -->

- [Introduction](#introduction)
    - [Setup of local system prior to running](#setup-of-local-system-prior-to-running)
    - [Networking connection](#networking-connection)
    - [Set the address on the Ethernet connection to the gateway](#set-the-address-on-the-ethernet-connection-to-the-gateway)
- [Running this script from a Python virtual environment](#running-this-script-from-a-python-virtual-environment)

<!-- /TOC -->

## Introduction

The steps in the process are as follows.  All are automated.

### Setup of local system prior to running

Look at the gateways you went to configure. The supported models are MTCDT 200 series ("blue boxes") and the MTCAP series ("white boxes").

Download the mLinux firmware image(s) you need and put them in a convenient directory. On Linux, `/tmp` is a particularly convenient place, because that's where the script looks.  At time of writing, the images could be downloaded with the following commands:

```bash
# change to wherever you want to put the images. /tmp is convenient but
# is reset after each boot.
cd /tmp

# get the MTCDT images
wget https://ttni.tech/mlinux/images/mtcdt/5.3.31/ttni-base-image-mtcdt-upgrade.bin
# get the MTCAP image
wget https://ttni.tech/mlinux/images/mtcap/5.3.31/ttni-base-image-mtcao-upgrade.bin
```

### Networking connection

We assume use of USB Ethernet adapters, so (1) you must attach at least one, and (2) you need to remove them from Network Manager's scope of control.

We follow instructions from [Redhat](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/configuring-networkmanager-to-ignore-certain-devices_configuring-and-managing-networking#configuring-networkmanager-to-ignore-certain-devices_configuring-and-managing-networking).

All our USB Ethernet adapters are ASIX-based, so we can simply remove any ASIX-based adapter from the list by matching, using the OUI to reduce the chance of mismatch.

All our USB Ethernet adapters have a common OUI, 000ec6, so we can match the patern `enx000ec6*` in the instructions that make them manually configured.

1. Create a file `/etc/NetworkManager/conf.d/99-unmanaged-asix-000ec6.conf`, containing:

    ```ini
    [keyfile]
    unmanaged-devices=interface-name:enx000ec6*
    ```

2. Restart network manager:

    ```bash
    sudo systemctl reload NetworkManager
    ```

3. Verify using `nmcli`, as shown below.

    ```console
    $ nmcli device status
    DEVICE           TYPE      STATE                   CONNECTION
    wlp3s0           wifi      connected               1140 Office Suites
    lo               loopback  connected (externally)  lo
    enp0s25          ethernet  unavailable             --
    enx000ec645f41e  ethernet  unmanaged               --
    enx000ec64601bc  ethernet  unmanaged               --
    enx000ec64601f0  ethernet  unmanaged               --
    enx000ec6460681  ethernet  unmanaged               --
    enx000ec646073d  ethernet  unmanaged               --
    enx000ec646174d  ethernet  unmanaged               --
    enx000ec6461879  ethernet  unmanaged               --
    enx000ec683120d  ethernet  unmanaged               --
    $ # note the "unmanaged"   ^^^^^^^^^
    ```

### Set the address on the Ethernet connection to the gateway

Connect a gateway via Ethernet to a USB NIC. For the USB NICs I use, I have the addresses printed on the side; but most NICs have the address somewhere on the manufacturer's label.

In this case, the adapter is labeled `00-0e-c6-46-17-4d`, which means that the corresponding Linux name is `enx000ec646174d`.

We manually set the IPv4 address of that NIC using `ifconfig`.

```bash
sudo ifconfig enx000ec646174d inet 192.168.2.200 netmask 255.255.255.0
```

If you want to set up multiple gateways concurrently, you can do so using VRF; see below.

## Set up this script from a Python virtual environment

This is the recommended approach, as it doesn't require making any global environment changes other than installing python3.  We tested with Python 3.12.3.

```bash
git clone git@github.com:things-nyc/aep_to_ttn_mlinux
cd aep_to_ttn_mlinux

# after cloning, create the .venv
python3 -m venv .venv

# set up the virtual environment
source .venv/bin/activate

# get the remaining requirements into the virtual environment
python3 -m pip install -r requirements.txt

# make sure the script is functional
python3 -m aep_to_ttn_mlinux --help
```

## Run the script

```bash
# make sure you've activated the venv, then:
python -m aep_to_ttn_linux --password choose-a-passw0rd --verbose
```

We normally use a different password than `choose-a-passw0rd`. Note that AEP wants a password containing lower case letters, digits, and punctuation.

## Setting up VRFs to allow configuring gateways in parallel

We relied on this [Redhat documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_networking/reusing-the-same-ip-address-on-different-interfaces_configuring-and-managing-networking#temporarily-reusing-the-same-ip-address-on-different-interfaces_reusing-the-same-ip-address-on-different-interfaces) to help figure out how to do this.

```bash
# set up VRFs
sudo ip link add vrf-usb1 type vrf table 10
sudo ip link set dev vrf-usb1 up
sudo route add table 10 unreacable default metric 4278198272
sudo route add table 10 unreachable default metric 4278198272

sudo ip link add vrf-usb2 type vrf table 11
sudo ip link set dev vrf-usb2 up
sudo ip route add table 10 unreachable default metric 4278198272
sudo ip route add table 11 unreachable default metric 4278198272

# .. and so forth.

# then put each USB interface into its own VRF
sudo ip link set dev enx000ec646174d master vrf-usb1
# ...

# show what is up (example).
sudo ip -d link show master vrf-usb1
sudo ip -d link show vrf vrf-usb1
sudo ip neigh show vrf vrf-usb1
sudo ip addr show vrf vrf-usb1

# demo that we can't reach a Conduit normally
ssh mtadm@192.168.2.1

# demo that we *can* reach it with ip vrf exec
sudo ip vrf exec vrf-usb1 ssh mtadm@192.168.2.1

# run the provisioning script
sudo ip vrf exec vrf-usb1 python -m aep_to_ttn_linux --password choose-a-passw0rd --verbose
```
