#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
import argparse
import os
import shutil
import sys
import traceback

import generator
from driver import generate_driver
from dtsi import generate_panel_dtsi
from fdt2 import Fdt2
from lk import generate_lk_driver
from panel import Panel
from simple import generate_panel_simple


def generate(p: Panel, options: generator.Options) -> None:
	print(f"Generating: {p.id} ({p.name})")

	if os.path.exists(p.id):
		shutil.rmtree(p.id)
	os.mkdir(p.id)

	if not args.backlight:
		p.backlight = None

	generate_panel_simple(p)
	generate_driver(p, options)
	generate_panel_dtsi(p, options)
	generate_lk_driver(p)


parser = argparse.ArgumentParser(
	description="Generate Linux DRM panel driver based on (downstream) MDSS DSI device tree")
parser.add_argument('dtb', nargs='+', type=argparse.FileType('rb'), help="Device tree blobs to parse")
parser.add_argument('-p', '--panel', help="""
	Specific panel node name or ID to generate config for.
	If omitted, the tool will list available panels in the DTB.
""")
parser.add_argument('-r', '--regulator', action='append', nargs='?', const='power', help="""
	Enable one or multiple regulators with the specified name in the generated panel driver.
	Some panels require additional power supplies to be enabled to work properly.
""")
parser.add_argument('--backlight-gpio', action='store_true', help="""
	Enable/disable backlight with an extra GPIO (works only for MIPI DCS backlight)
""")
parser.add_argument('--no-backlight', dest='backlight', action='store_false', default=True, help="""
	Do not generate any backlight/brightness related code.
""")
parser.add_argument('--backlight-fallback-dcs', action='store_true', help="""
	Generate code for both custom backlight and DCS backlight. DCS backlight
	is used if no 'backlight' is defined in the device tree.
""")
parser.add_argument('--dcs-no-get-brightness', dest='dcs_get_brightness', action='store_false', default=True, help="""
	Do not generate get_brightness() function for DCS backlight/brightness code.
	Some panels do not implement the MIPI DCS Get Display Brightness command correctly.
""")
parser.add_argument('--ignore-wait', type=int, default=0, help="""
	Ignore wait in command sequences that is smaller that the specified value.
	Some device trees add a useless 1ms wait after each command, making the driver
	unnecessarily verbose.
""")
parser.add_argument('--dumb-dcs', dest='dumb_dcs', action='store_true', help="""
	Do not attempt to interpret DCS commands. Some panels use arbitrary DCS commands
	to write to registers, which conflict with commands specified in the MIPI DCS
	specification. This option stops interpretation of DCS commands, except for
	enter/exit_sleep_mode and set_display_on/off (which should be supported by
	any panel ideally).
""")
args = parser.parse_args(namespace=generator.Options())

if not args.panel:
	print("No panel specified. Listing available panels...")
	print("-" * 50)

for f in args.dtb:
	with f:
		if args.panel:
			print(f"Scanning {f.name} for panel '{args.panel}'...")
		else:
			print(f"Parsing: {f.name}")

		fdt = Fdt2(f.read())

		found = False
		for offset in Panel.find(fdt):
			try:
				if not args.panel:
					info = Panel.parse(fdt, offset, list_only=True)
					if info:
						print(f"  - {info[0]} (ID: {info[1]})")
						found = True
				else:
					panel = Panel.parse(fdt, offset, target_panel=args.panel)
					if panel:
						generate(panel, args)
						found = True
						break
			except Exception:
				if not args.panel:
					traceback.print_exc(file=sys.stdout)
				continue

if not args.panel:
	print("-" * 50)
	print("Run the command again and supply -p <panel_name> or -p <panel_id> to generate a driver.")
	sys.exit(0)
