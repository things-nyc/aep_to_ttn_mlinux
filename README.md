# `aep_to_ttn_mlinux`

`aep_to_ttn_mlinux` is used to configure a MultiTech Conduit with AEP firmware that is in commissioning mode. It configures the Conduit for use with the [IthacaThings administration system](https://github.com/IthacaThings/ttn-multitech-cm) by Jeff Honig.

<!-- TOC depthfrom:2 updateonsave:true -->

- [Introduction](#introduction)
    - [Setup of local system prior to running](#setup-of-local-system-prior-to-running)
    - [Networking connection](#networking-connection)
        - [Using the main Ethernet adapter](#using-the-main-ethernet-adapter)
        - [Using USB Adapters](#using-usb-adapters)
- [Set up this script using a Python virtual environment](#set-up-this-script-using-a-python-virtual-environment)
- [Run the script](#run-the-script)
- [Setting up VRFs to allow configuring gateways in parallel](#setting-up-vrfs-to-allow-configuring-gateways-in-parallel)

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
wget https://ttni.tech/mlinux/images/mtcap/5.3.31/ttni-base-image-mtcap-upgrade.bin
```

### Networking connection

If you're willing to hack on your main Ethernet connection of your computer, see [the very next section](#using-the-main-ethernet-adapter). Otherwise if you want to configure lots of devices at once, skip down to ["Using USB Adapters"](#using-usb-adapters).

#### Using the main Ethernet adapter

You must remove the main Ethernet adapter from Ubunu Network Manager's scope of control, because it will try to automatically mess things up while you're trying to use the adapter in a special pre-determined way.

1. Disconnect the Ethernet cable from your Ethernet port.
2. Get the name of your Ethernet adapter using `ifconfig`. It will usually be something like `enp0s025`. You can also use `nmcli device status`, which will show it as a managed adapter in the `unconnected` state. For example:

    ```bash
    $ nmcli device status
    VICE   TYPE      STATE                   CONNECTION
    wlp3s0   wifi      connected               WeWorkGuest
    lo       loopback  connected (externally)  lo
    docker0  bridge    connected (externally)  docker0
    enp0s25  ethernet  unavailable             --
    $
    ```

   The word `unavailable` is your signal that the adapter is *managed*, but not *connected*.  We want it to say `unmanaged`, and we do this in the following steps.

3. Create a file `/etc/NetworkManager/conf.d/99-unmanaged-enp0s25.conf`.  The name is somewhat arbitrary, although it must end with `.conf`. The `99-` has to do with the order of processing by Network Manager; the rest of the name `unmanaged-enp0s25` is intended to remind us of the contents and purpose of the file, that is "make enp0s25 unmanaged". The file must contain:

    ```ini
    [keyfile]
    unmanaged-devices=interface-name:enp0s25
    ```

   You will need to change `enp0s25` to match the name of the Ethernet adapter on your machine. Nothing else should be changed in this file.

4. Change the ownership and permissions of the file you just created.

   ```bash
   # change owner to root
   $ sudo chown root /etc/NetworkManager/conf.d/99-unmanaged-enp0s25.conf

   # change permissions:
   #   "read/write by owner"
   #   "read-only for everyone else"
   $ sudo chmod 644 /etc/NetworkManager/conf.d/99-unmanaged-enp0s25.conf
   ```

5. Restart network manager:

    ```bash
    sudo systemctl reload NetworkManager
    ```

6. Verify using `nmcli`, as shown below.

    ```console
    $ nmcli device status
    DEVICE           TYPE      STATE                   CONNECTION
    wlp3s0           wifi      connected               1140 Office Suites
    lo               loopback  connected (externally)  lo
    enp0s25          ethernet  unmanged                --
    ```

7. Manually set the IPv4 address of the Ethernet adapter using `ifconfig`.

    ```bash
    sudo ifconfig enp0s25 inet 192.168.2.200 netmask 255.255.255.0
    ```

   Again, change `enp0s25` to match whatever name Linux uses for your Ethernet adapter.

#### Using USB Adapters

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

Connect a gateway via Ethernet to a USB NIC. For the USB NICs I use, I have the addresses printed on the side; but most NICs have the address somewhere on the manufacturer's label.

In this case, the adapter is labeled `00-0e-c6-46-17-4d`, which means that the corresponding Linux name is `enx000ec646174d`.

We manually set the IPv4 address of that NIC using `ifconfig`.

```bash
sudo ifconfig enx000ec646174d inet 192.168.2.200 netmask 255.255.255.0
```

If you want to set up multiple gateways concurrently, you can do so using VRF; see below.

## Set up this script using a Python virtual environment

This is the recommended approach, as it doesn't require making any global environment changes other than installing python3.  We tested with Python 3.12.3. A Makefile is provided to make things work.

You normally only need to do this step after updating the repo from github, but it doens't hurt.

```bash
# get a copy of the Git repo
# you can use https://github.com/things-nyc/aep_to_ttn_mlinux
# if you just want a quick copy w/o logging into github.
git clone git@github.com:things-nyc/aep_to_ttn_mlinux

# go to the top-level of what you just checked out
cd aep_to_ttn_mlinux

# reset everything for a clean start
$ make distclean
rm -rf .buildenv .venv *.egg-info */__pycache__
rm -rf dist

# after cloning, create the .venv
$ make venv
python3 -m venv .venv
. .venv/bin/activate && python -m pip install -r requirements.txt
Collecting requests>=2.31.0 (from -r requirements.txt (line 1))
  Using cached requests-2.32.5-py3-none-any.whl.metadata (4.9 kB)
Collecting urllib3>=2.0.7 (from -r requirements.txt (line 2))
  Using cached urllib3-2.5.0-py3-none-any.whl.metadata (6.5 kB)
Collecting fabric>=3.2.2 (from -r requirements.txt (line 3))
  Using cached fabric-3.2.2-py3-none-any.whl.metadata (3.5 kB)
Collecting charset_normalizer<4,>=2 (from requests>=2.31.0->-r requirements.txt (line 1))
  Using cached charset_normalizer-3.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (37 kB)
Collecting idna<4,>=2.5 (from requests>=2.31.0->-r requirements.txt (line 1))
  Using cached idna-3.11-py3-none-any.whl.metadata (8.4 kB)
Collecting certifi>=2017.4.17 (from requests>=2.31.0->-r requirements.txt (line 1))
  Using cached certifi-2025.11.12-py3-none-any.whl.metadata (2.5 kB)
Collecting invoke>=2.0 (from fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached invoke-2.2.1-py3-none-any.whl.metadata (3.3 kB)
Collecting paramiko>=2.4 (from fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached paramiko-4.0.0-py3-none-any.whl.metadata (3.9 kB)
Collecting decorator>=5 (from fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached decorator-5.2.1-py3-none-any.whl.metadata (3.9 kB)
Collecting deprecated>=1.2 (from fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached deprecated-1.3.1-py2.py3-none-any.whl.metadata (5.9 kB)
Collecting wrapt<3,>=1.10 (from deprecated>=1.2->fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached wrapt-2.0.1-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (9.0 kB)
Collecting bcrypt>=3.2 (from paramiko>=2.4->fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached bcrypt-5.0.0-cp39-abi3-manylinux_2_34_x86_64.whl.metadata (10 kB)
Collecting cryptography>=3.3 (from paramiko>=2.4->fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached cryptography-46.0.3-cp311-abi3-manylinux_2_34_x86_64.whl.metadata (5.7 kB)
Collecting pynacl>=1.5 (from paramiko>=2.4->fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached pynacl-1.6.1-cp38-abi3-manylinux_2_34_x86_64.whl.metadata (9.8 kB)
Collecting cffi>=2.0.0 (from cryptography>=3.3->paramiko>=2.4->fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (2.6 kB)
Collecting pycparser (from cffi>=2.0.0->cryptography>=3.3->paramiko>=2.4->fabric>=3.2.2->-r requirements.txt (line 3))
  Using cached pycparser-2.23-py3-none-any.whl.metadata (993 bytes)
Using cached requests-2.32.5-py3-none-any.whl (64 kB)
Using cached urllib3-2.5.0-py3-none-any.whl (129 kB)
Using cached fabric-3.2.2-py3-none-any.whl (59 kB)
Using cached certifi-2025.11.12-py3-none-any.whl (159 kB)
Using cached charset_normalizer-3.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (153 kB)
Using cached decorator-5.2.1-py3-none-any.whl (9.2 kB)
Using cached deprecated-1.3.1-py2.py3-none-any.whl (11 kB)
Using cached idna-3.11-py3-none-any.whl (71 kB)
Using cached invoke-2.2.1-py3-none-any.whl (160 kB)
Using cached paramiko-4.0.0-py3-none-any.whl (223 kB)
Using cached bcrypt-5.0.0-cp39-abi3-manylinux_2_34_x86_64.whl (278 kB)
Using cached cryptography-46.0.3-cp311-abi3-manylinux_2_34_x86_64.whl (4.5 MB)
Using cached pynacl-1.6.1-cp38-abi3-manylinux_2_34_x86_64.whl (1.4 MB)
Using cached wrapt-2.0.1-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (121 kB)
Using cached cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (219 kB)
Using cached pycparser-2.23-py3-none-any.whl (118 kB)
Installing collected packages: wrapt, urllib3, pycparser, invoke, idna, decorator, charset_normalizer, certifi, bcrypt, requests, deprecated, cffi, pynacl, cryptography, paramiko, fabric
Successfully installed bcrypt-5.0.0 certifi-2025.11.12 cffi-2.0.0 charset_normalizer-3.4.4 cryptography-46.0.3 decorator-5.2.1 deprecated-1.3.1 fabric-3.2.2 idna-3.11 invoke-2.2.1 paramiko-4.0.0 pycparser-2.23 pynacl-1.6.1 requests-2.32.5 urllib3-2.5.0 wrapt-2.0.1
Virtual environment created in .venv.

To activate in bash, say:
    . .venv/bin/activate

Then be sure to run the app using python (not python3)
$
```

At this point, make sure it's all set up correctly.

```bash
# make sure the script is functional
$ python -m aep_to_ttn_mlinux --help
usage: aep_to_ttn_mlinux [-h] [-d] [--nodebug] [-v] [-n] [--version]
                         [--username USERNAME] --password PASSWORD
                         [--address ADDRESS] [-f] [--skip-password]
                         [--product-type PRODUCT_TYPE]
                         [--product-id PRODUCT_ID] [--image IMAGE_FILE]
                         [--reboot_time REBOOT_TIME]

Download TTN mLinux to Conduit AEP using the commissioning API and ssh. If the
Conduit has not already been given an administrative login and password, this
script will set them (using the values of --username and --password). The
script then uses the commissioning API to enable SSH (if not already enabled.)
When enabling ssh, a reboot is forced, and the script waits for the reboot to
complete. Then the script uses ssh to download the appropriate image for the
Conduit being configured. Finally, the script triggers a firmware update. The
script does not wait for the firmware update to complete.

options:
  -h, --help            show this help message and exit
  --version             Print version and exit.

Debugging options:
  -d, --debug           Print debugging messages.
  --nodebug             Do not print debugging messages.
  -v, --verbose         Print verbose messages.
  -n, --noop, --dry-run
                        Don't make changes, just list what we are going to do.

Configuration options:
  --username USERNAME, --user USERNAME, -U USERNAME
                        Username to use to connect (default mtadm).
  --password PASSWORD, --pass PASSWORD, -P PASSWORD
                        Password to use to connect. There is no default; this
                        must always be supplied.
  --address ADDRESS, -A ADDRESS
                        IP address of the conduit being commissioned (default
                        192.168.2.1).
  -f, --force           Forcibly update the ssh settings and reboot the
                        Conduit, even if already set.
  --skip-password, -S   Assume username and password are already set in the
                        Conduit.
  --product-type PRODUCT_TYPE
                        Default product type, normally mtcdt or mtcap;
                        default: read from device. If specified, and the
                        discovered product type doesn't match, the script will
                        abort.
  --product-id PRODUCT_ID
                        Full product ID, normally mctdt-l4n1-247a or similar;
                        default: read from device. If specified, and the
                        discovered product ID doesn't match, the script will
                        abort.
  --image IMAGE_FILE    Path to mLinux image to be downloaded; use
                        {product_type} to insert the product type dynamically.
                        (Default: /tmp/ttni-base-
                        image-{product_type}-upgrade.bin)
  --reboot_time REBOOT_TIME
                        How long to wait for reboots, in seconds (default
                        600).
```

## Run the script

Boot up the AEP gateway, and connect its networking port to your Ethernet adapter.

```bash
# make sure you've activated the venv, then:
python -m aep_to_ttn_mlinux --password choose-a-passw0rd --verbose
```

We normally use a different password than `choose-a-passw0rd`. Note that AEP wants a password containing lower case letters, digits, and punctuation.

If the Conduit has not already been given an administrative login and password, this script will set them (using the values of `--username` and `--password`).

The script then uses the commissioning API to enable SSH (if not already enabled.)
When enabling ssh, a reboot is forced, and the script waits for the reboot
to complete.

Then the script uses ssh to download the appropriate image for the
Conduit being configured.

Finally, the script triggers a firmware update.

The script does not wait for the firmware update to complete.

Thus, you'll normally observe two reboots of the Conduit -- the first time to enable SSH, and the second time to do the firmware update.

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
sudo ip vrf exec vrf-usb1 python -m aep_to_ttn_mlinux --password choose-a-passw0rd --verbose
```
