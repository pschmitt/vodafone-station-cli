#!/usr/bin/env python3
"""Test script for aiovodafone library."""

import asyncio
import json
import logging
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import asdict
from pathlib import Path

from aiohttp import ClientSession, CookieJar
from rich import box, print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aiovodafone.api import (
    VodafoneStationCommonApi,
    VodafoneStationSercommApi,
    VodafoneStationTechnicolorApi,
)
from aiovodafone.const import DeviceType
from aiovodafone.exceptions import (
    AlreadyLogged,
    CannotAuthenticate,
    CannotConnect,
    GenericLoginError,
    ModelNotSupported,
    VodafoneError,
)

console = Console()
LOGGER = logging.getLogger(__name__)


def parse_args() -> Namespace:
    """Get parsed passed in arguments."""
    parser = ArgumentParser(description="aiovodafone library test")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug mode",
    )
    parser.add_argument(
        "--router",
        "-r",
        type=str,
        default="192.168.0.1",
        help="Set router IP address",
    )
    parser.add_argument(
        "--username",
        "-u",
        type=str,
        default="admin",
        help="Set router username",
    )
    parser.add_argument(
        "--password",
        "-p",
        type=str,
        help="Set router password",
        required=True,
    )
    parser.add_argument(
        "-F",
        "--force",
        action="store_true",
        default=False,
        help="Force disconnect other users",
    )
    parser.add_argument(
        "--configfile",
        "-cf",
        type=str,
        help="Load options from JSON config file. \
    Command line options override those in the file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output JSON instead of human-readable text",
    )

    # Create subparsers for different actions
    subparsers = parser.add_subparsers(dest="ACTION", required=True)

    # Info (no additional arguments)
    info_parser = subparsers.add_parser(
        "info", help="Retrieve router information"
    )
    info_parser.add_argument(
        "info_type",
        nargs="?",  # Allows zero or one argument
        choices=["voice", "docsis", "device", "settings", "all", "clients"],
        help="Specify which info to display (voice, docsis, device, etc.).",
    )

    # LED control
    led_parser = subparsers.add_parser(
        "led", aliases=["l", "leds"], help="LED control"
    )
    led_parser.add_argument("STATE", choices=["on", "off"], help="LED state")

    # Restart
    subparsers.add_parser("restart", aliases=["reboot"], help="Restart router")

    # Ping
    ping_parser = subparsers.add_parser("ping", help="Ping a target")
    ping_parser.add_argument("TARGET", type=str, help="IP address to ping")
    ping_parser.add_argument(
        "--count", type=int, default=1, help="Number of pings"
    )
    ping_parser.add_argument(
        "--size", type=int, default=56, help="Ping packet size"
    )
    ping_parser.add_argument(
        "--interval",
        type=int,
        default=1000,
        help="Ping interval in milliseconds",
    )
    ping_parser.add_argument(
        "--retries", type=int, default=15, help="Retry count"
    )

    # Traceroute
    traceroute_parser = subparsers.add_parser(
        "traceroute", help="Perform a traceroute"
    )
    traceroute_parser.add_argument(
        "TARGET", type=str, help="IP address to traceroute"
    )
    traceroute_parser.add_argument(
        "--count",
        type=int,
        default=30,
        help="Max number of hops",
    )
    traceroute_parser.add_argument(
        "--ip-type",
        type=str,
        choices=["Ipv4", "Ipv6"],
        default="Ipv4",
        help="IP type",
    )
    traceroute_parser.add_argument(
        "--retries",
        type=int,
        default=15,
        help="Retry count",
    )

    # DNS Resolve
    dns_parser = subparsers.add_parser("dns", help="Resolve a hostname")
    dns_parser.add_argument("TARGET", type=str, help="Hostname to resolve")
    dns_parser.add_argument(
        "--dns-server",
        type=str,
        default="1.1.1.1",
        help="DNS server to use",
    )
    dns_parser.add_argument(
        "--record-type",
        type=str,
        choices=["A", "AAAA", "CNAME", "MX", "TXT"],
        default="A",
        help="DNS record type",
    )
    dns_parser.add_argument(
        "--retries", type=int, default=15, help="Retry count"
    )

    arguments = parser.parse_args()
    # Re-parse the command line with the JSON config if provided
    if arguments.configfile and Path(arguments.configfile).exists():
        with Path.open(arguments.configfile) as f:
            arguments = parser.parse_args(namespace=Namespace(**json.load(f)))

    return arguments


async def gather_info_data(
    api: VodafoneStationCommonApi,
    info_type: str | None = None,
) -> dict:
    """Gather info data in a dict (for JSON output).

    This mirrors what display_device_info() prints using Rich.
    """
    data = {}

    if info_type in ("all", None, "clients"):
        client_data = await api.get_devices_data()
        data["clients"] = []
        for device in client_data.values():
            # Convert the dataclass instance to a dictionary
            device_dict = asdict(device)
            # Rename 'device_type' back to 'type' if needed
            if "device_type" in device_dict:
                device_dict["type"] = device_dict.pop("device_type")
            data["clients"].append(device_dict)

    if info_type in ("all", None, "device"):
        sensor_data = await api.get_sensor_data()
        data["device"] = {
            "serial_number": sensor_data.get("sys_serial_number", "N/A"),
            "firmware": sensor_data.get("sys_firmware_version", "N/A"),
            "hardware": sensor_data.get("sys_hardware_version", "N/A"),
            "uptime_seconds": sensor_data.get("sys_uptime", 0),
            "wan_status": sensor_data.get("wan_status", "N/A"),
            "cm_status": sensor_data.get("cm_status", "N/A"),
            "lan_mode": sensor_data.get("lan_mode", "N/A"),
        }

    if info_type in ("all", None, "settings") and isinstance(
        api,
        VodafoneStationTechnicolorApi,
    ):
        device_settings_data = await api.get_devices_data()
        data["settings"] = {
            "led": device_settings_data.get("led", "N/A"),
        }

    if info_type in ("all", None, "docsis"):
        docsis_data = await api.get_docis_data()
        data["docsis"] = {"downstream": {}, "upstream": {}}
        for which in ["downstream", "upstream"]:
            data["docsis"][which] = {}
            for channel, values in docsis_data.get(which, {}).items():
                data["docsis"][which][channel] = {
                    "channel_type": values.get("channel_type", "N/A"),
                    "channel_frequency": values.get(
                        "channel_frequency", "N/A"
                    ),
                    "channel_modulation": values.get(
                        "channel_modulation", "N/A"
                    ),
                    "channel_power": values.get("channel_power", "N/A"),
                    "channel_locked": values.get("channel_locked", "N/A"),
                }

    if info_type in ("all", None, "voice"):
        voice_data = await api.get_voice_data()
        data["voice"] = {
            "general_status": voice_data["general"].get("status", "N/A"),
            "line1": {
                "status": voice_data["line1"].get("status", "N/A"),
                "call_number": voice_data["line1"].get("call_number", "N/A"),
                "line_status": voice_data["line1"].get("line_status", "N/A"),
            },
            "line2": {
                "status": voice_data["line2"].get("status", "N/A"),
                "call_number": voice_data["line2"].get("call_number", "N/A"),
                "line_status": voice_data["line2"].get("line_status", "N/A"),
            },
        }

    return data


async def display_device_info(
    api: VodafoneStationCommonApi,
    info_type: str | None = None,
) -> None:
    """Display device info based on selected info type using Rich."""
    if info_type in ("all", None, "device"):
        sensor_data = await api.get_sensor_data()
        LOGGER.debug("Sensor data: %s", sensor_data)

        table = Table(title="Device Information", box=box.SIMPLE)
        table.add_column("Property", style="cyan", justify="right")
        table.add_column("Value", style="white")

        table.add_row("Serial #", sensor_data.get("sys_serial_number", "N/A"))
        table.add_row(
            "Firmware", sensor_data.get("sys_firmware_version", "N/A")
        )
        table.add_row(
            "Hardware", sensor_data.get("sys_hardware_version", "N/A")
        )
        table.add_row(
            "Uptime",
            str(api.convert_uptime(sensor_data.get("sys_uptime", 0))),
        )
        table.add_row("WAN status", sensor_data.get("wan_status", "N/A"))
        table.add_row(
            "Cable modem status", sensor_data.get("cm_status", "N/A")
        )
        table.add_row("LAN mode", sensor_data.get("lan_mode", "N/A"))

        console.print(table)

    if info_type in ("all", None, "settings") and isinstance(
        api,
        VodafoneStationTechnicolorApi,
    ):
        device_settings_data = await api.get_devices_data()
        LOGGER.debug("Device data: %s", device_settings_data)

        table = Table(title="Device Settings", box=box.SIMPLE)
        table.add_column("Property", style="cyan", justify="right")
        table.add_column("Value", style="white")
        table.add_row("LED", device_settings_data.get("led", "N/A"))
        console.print(table)

    if info_type in ("all", None, "docsis"):
        docsis_data = await api.get_docis_data()
        LOGGER.debug("DOCSIS data: %s", docsis_data)

        for which in ["downstream", "upstream"]:
            console.print(
                Panel(
                    Text(which.capitalize(), style="bold magenta"),
                    expand=False,
                ),
            )
            docis_table = Table(
                title=f"{which.capitalize()} Channels", box=box.SIMPLE
            )
            docis_table.add_column("Channel", style="cyan")
            docis_table.add_column("Type", style="green")
            docis_table.add_column("Frequency", style="yellow")
            docis_table.add_column("Modulation", style="blue")
            docis_table.add_column("Power", style="red")
            docis_table.add_column("Locked", style="white")

            for channel, values in docsis_data[which].items():
                docis_table.add_row(
                    channel,
                    values.get("channel_type", "N/A"),
                    str(values.get("channel_frequency", "N/A")),
                    values.get("channel_modulation", "N/A"),
                    str(values.get("channel_power", "N/A")),
                    str(values.get("channel_locked", "N/A")),
                )

            console.print(docis_table)

    if info_type in ("all", None, "voice"):
        voice_data = await api.get_voice_data()
        LOGGER.debug("voice data: %s", voice_data)

        voice_table = Table(title="VoIP Information", box=box.SIMPLE)
        voice_table.add_column("Line", style="cyan")
        voice_table.add_column("Status", style="green")
        voice_table.add_column("Number", style="yellow")
        voice_table.add_column("Line Status", style="blue")

        voice_table.add_row(
            "General",
            voice_data["general"].get("status", "N/A"),
            "-",
            "-",
        )
        voice_table.add_row(
            "Line1",
            voice_data["line1"].get("status", "N/A"),
            voice_data["line1"].get("call_number", "N/A"),
            voice_data["line1"].get("line_status", "N/A"),
        )
        voice_table.add_row(
            "Line2",
            voice_data["line2"].get("status", "N/A"),
            voice_data["line2"].get("call_number", "N/A"),
            voice_data["line2"].get("line_status", "N/A"),
        )

        console.print(voice_table)

    if info_type in ("all", None, "clients"):
        # Fetch client data
        client_data = await api.get_devices_data()
        LOGGER.debug("client data: %s", client_data)

        # Create a table for client information
        client_table = Table(title="Connected Clients", box=box.SIMPLE)
        client_table.add_column("Name", style="cyan")
        client_table.add_column("MAC Address", style="magenta")
        client_table.add_column("IP Address", style="yellow")
        client_table.add_column("Connection Type", style="green")
        client_table.add_column("Status", style="blue")

        # Populate the table with client data
        for device in client_data.values():
            device_dict = asdict(device)

            client_table.add_row(
                device_dict.get("name", "N/A"),
                device_dict.get("mac", "N/A"),
                device_dict.get("ip_address", "N/A"),
                device_dict.get("connection_type", "N/A"),
                (
                    "Connected"
                    if device_dict.get("connected", False)
                    else "Disconnected"
                ),
            )

        # Print the table
        console.print(client_table)


async def connect(
    hostname: str = "192.168.0.1",
    username: str = "admin",
    password: str = "",
    force: bool = False,
) -> VodafoneStationCommonApi:
    """Connect to the router and return the api client."""
    jar = CookieJar(unsafe=True)
    session = ClientSession(cookie_jar=jar)
    device_type = await VodafoneStationCommonApi.get_device_type(
        hostname,
        session,
    )
    api: VodafoneStationCommonApi
    if device_type == DeviceType.TECHNICOLOR:
        api = VodafoneStationTechnicolorApi(
            hostname, username, password, session=session
        )
    elif device_type == DeviceType.SERCOMM:
        api = VodafoneStationSercommApi(
            hostname, username, password, session=session
        )
    else:
        LOGGER.error("The device is not a supported Vodafone Station.")
        sys.exit(1)

    try:
        try:
            await api.login(force_logout=force)
        except ModelNotSupported:
            LOGGER.exception(
                "Model is not supported yet for router %s", api.host
            )
            raise
        except CannotAuthenticate:
            LOGGER.exception("Cannot authenticate to router %s", api.host)
            raise
        except CannotConnect:
            LOGGER.exception("Cannot connect to router %s", api.host)
            raise
        except AlreadyLogged:
            LOGGER.exception(
                "Only one user at a time can connect to router %s",
                api.host,
            )
            raise
        except GenericLoginError:
            LOGGER.exception("Unable to login to router %s", api.host)
            raise
    except VodafoneError:
        await api.close()
        sys.exit(1)

    return api


async def main() -> None:
    """Run main."""
    args = parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        LOGGER.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("asyncio").setLevel(logging.INFO)
        logging.getLogger("charset_normalizer").setLevel(logging.INFO)
        LOGGER.debug("Arguments: %s", args)

    api = await connect(args.router, args.username, args.password, args.force)

    rc = 0
    res = None

    if args.ACTION == "info":
        if args.json:
            # Gather info in a dict and print as JSON
            info_data = await gather_info_data(api, args.info_type)
            if args.info_type not in (None, "all", ""):
                info_data = info_data.get(args.info_type)
            print_json(json.dumps(info_data))
        else:
            # Use the existing Rich-based display
            await display_device_info(api, args.info_type)

    elif args.ACTION in ["l", "led", "leds"]:
        res = await api.set_led_state(args.STATE == "on")
    elif args.ACTION in ["restart", "reboot"]:
        LOGGER.info("Rebooting router...")
        sys.exit(await api.restart_router())
    elif args.ACTION == "dns":
        LOGGER.debug("ping %s", args.TARGET)
        res = await api.dns_resolve(args.TARGET)
    elif args.ACTION == "ping":
        LOGGER.debug("Resolve %s", args.TARGET)
        res = await api.ping(args.TARGET)
    elif args.ACTION == "traceroute":
        LOGGER.debug("Traceroute %s", args.TARGET)
        res = await api.traceroute(args.TARGET)
    else:
        LOGGER.error("Unknown action: %s", args.ACTION)
        rc = 2

    # For commands that return a 'res' with 'data', we still print
    # JSON unconditionally.
    if res:
        print_json(json.dumps(res.get("data")))

    LOGGER.debug("Logout & close session")
    await api.logout()
    await api.close()
    sys.exit(rc)


def cli() -> None:
    """Entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
