import configparser
import importlib
import os
import re
from . import config_syntax
from ..bench.engine import EngineBase
from ..environment import hardware as env_hw

from ..utils import helpers as h


class Config:
    def __init__(self, config_file: str, hardware: env_hw.Hardware):
        self.config_file = config_file
        if not os.path.isfile(self.config_file):
            h.fatal(f"File '{self.config_file}' does not exists.")

        # Ensure default options from the configuration file
        default_parameters = {
            "runtime": "60",
            "monitor": "none",
            "stressor_range": "1",
            "stressor_range_scaling": "plus_1",
            "hosting_cpu_cores": "none",
            "hosting_cpu_cores_scaling": "iterate",
        }
        self.config = configparser.RawConfigParser(
            default_section="global", defaults=default_parameters
        )
        self.hardware = hardware
        self.config.read(self.config_file)

    def get_sections(self) -> list[str]:
        """Return all sections of a config file."""
        return self.config.sections()

    def get_section(self, section_name) -> configparser.SectionProxy:
        """Return one section of a config file"""
        return self.config[section_name]

    def get_valid_keywords(self) -> list[str]:
        """Return the list of valid keywords."""
        return [
            "runtime",
            "monitor",
            "engine",
            "engine_module",
            "engine_module_parameter",
            "stressor_range",
            "stressor_range_scaling",
            "hosting_cpu_cores",
            "hosting_cpu_cores_scaling",
            "thermal_start",
            "fans_start",
        ]

    def get_directive(self, section_name, directive) -> str:
        """Return one directive of a section."""
        return self.get_section(section_name)[directive].lower()

    def get_runtime(self, section_name) -> int:
        """Return the runtime value of a section."""
        return int(self.get_directive(section_name, "runtime"))

    def get_monitor(self, section_name) -> str:
        """Return the monitor value of a section."""
        return self.get_directive(section_name, "monitor")

    def get_engine(self, section_name) -> str:
        """Return the engine value of a section."""
        return self.get_directive(section_name, "engine")

    def load_engine(self, engine_name) -> EngineBase:
        """Return the engine from <engine_name> type."""
        module = importlib.import_module(
            "..engines.{}".format(engine_name), package="hwbench.engines"
        )
        return module.Engine()

    def get_engine_module(self, section_name) -> str:
        """Return the engine module name of a section."""
        # If no engine_module is defined, considering the engine name
        try:
            engine_module = self.get_directive(section_name, "engine_module")
        except KeyError:
            engine_module = self.get_engine(section_name)
        return engine_module

    def get_engine_module_parameter(self, section_name) -> list[str]:
        """Return the engine module parameter name of a section."""
        # If no engine_module_parameter is defined, considering the engine_module name
        try:
            engine_module_parameter = self.get_directive(
                section_name, "engine_module_parameter"
            )
        except KeyError:
            engine_module_parameter = self.get_engine_module(section_name)
        return self.parse_range(engine_module_parameter)

    def get_stressor_range(self, section_name) -> list[str]:
        """Return the stressor range of a section."""
        return self.parse_range(self.get_directive(section_name, "stressor_range"))

    def get_stressor_range_scaling(self, section_name) -> str:
        """Return the stressor range scaling of a section."""
        return self.get_directive(section_name, "stressor_range_scaling")

    def get_hosting_cpu_cores(self, section_name) -> list[str]:
        """Return the hosting cpu cores of a section."""

        def get_cores_from_domain(domain):
            """Return the core list for a particular numa domain name"""
            core_list = self.hardware.get_cpu().get_logical_cores_in_numa_domain(
                int(domain)
            )
            if not core_list:
                h.fatal(f"NUMA domain {domain} does not exists")
            return core_list

        hcc = self.get_directive(section_name, "hosting_cpu_cores")

        # If the hcc has some numa domains, lets expand them.
        # Let's search if there is any numa keyword
        domains = re.findall(r"numa([0-9-,]+)", hcc)

        for domain in domains:
            cpus = ""
            ints = []
            # reuse the same parse_range function for a consistent syntax
            for value in self.parse_range(domain):
                ints += get_cores_from_domain(value)

            # Let's build the list of cpu for the selected numa domains
            cpus = ",".join(str(e) for e in sorted(ints))
            # Replace only the matched domain by the list of cpus
            hcc = hcc.replace(f"numa{domain}", cpus, 1)

        return self.parse_range(hcc)

    def get_hosting_cpu_cores_scaling(self, section_name) -> str:
        """Return the hosting cpu cores scaling of a section."""
        return self.get_directive(section_name, "hosting_cpu_cores_scaling")

    def is_valid_keyword(self, keyword) -> bool:
        """Return if a keyword is valid"""
        return keyword in self.get_valid_keywords()

    def validate_sections(self):
        """Validates all sections of a config file."""
        for section_name in self.get_sections():
            self.validate_section(section_name)

    def validate_section(self, section_name):
        """Validate <section_name> section of a config file."""
        for directive in self.get_section(section_name):
            if not self.is_valid_keyword(directive):
                h.fatal("job {}: invalid keyword {}".format(section_name, directive))
            # Execute the validations_<function> from config_syntax file
            # It will validate the syntax of this particular function.
            # An invalid syntax is fatal and halts the program
            validate_function = getattr(config_syntax, "validate_{}".format(directive))
            message = validate_function(
                self, section_name, self.get_section(section_name)[directive]
            )
            if message:
                h.fatal(f"Job {section_name}: keyword {directive} : {message}")

    def get_config(self) -> configparser.RawConfigParser:
        """Return the configuration object."""
        return self.config

    def parse_range(self, input: str) -> list[str]:
        """A function to parse the range syntax from a configuration directive."""
        result = []
        # FIXME: implement 'all'
        # group1 group2...
        groups_count = len(input.split(" "))

        for group in input.split(" "):
            # syntax: <x>,<y>
            current_group = []
            # Let's remove the [] if any
            for item in group.split(","):
                # syntax: <x>-<y>
                if "-" in item:
                    ranges = item.split("-")
                    if len(ranges) == 2:
                        if not ranges[0].isnumeric() or not ranges[1].isnumeric():
                            h.fatal(f"Non-numeric range {ranges} in '{input}'")
                        for cpu_number in range(int(ranges[0]), int(ranges[1]) + 1):
                            current_group.append(cpu_number)
                else:
                    # syntax: <x>
                    if item.isnumeric():
                        item = int(item)
                    current_group.append(item)
            if groups_count > 1:
                result.append(current_group)
            else:
                result = current_group
        return result
