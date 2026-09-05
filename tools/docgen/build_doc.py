import json, os

def load(dirpath):
    out = {}
    for fn in sorted(os.listdir(dirpath)):
        if fn.endswith(".json"):
            name = fn[:-5]
            with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                out[name] = json.load(f)
    return out

dt = load("dt")
oracle = load("oracle")
gui = load("gui")

def escape(s):
    return s.replace("|", "\\|") if s else s

def render_module(name, data, heading_level=3):
    lines = []
    h = "#" * heading_level
    lines.append(f"{h} `{name}.py`")
    lines.append("")
    if data["module_summary"]:
        lines.append(data["module_summary"])
        lines.append("")
    if not data["classes"] and not data["functions"]:
        exports = data.get("all_exports") or []
        if exports:
            lines.append("Re-exports the package's public API:")
            lines.append("")
            lines.append(", ".join(f"`{e}`" for e in exports))
            lines.append("")
        else:
            lines.append("_No public classes or functions (script / entry point)._")
            lines.append("")
        return "\n".join(lines)

    for cls in data["classes"]:
        bases = f"({', '.join(cls['bases'])})" if cls["bases"] else ""
        lines.append(f"**class `{cls['name']}{bases}`**")
        lines.append("")
        if cls["summary"]:
            lines.append(cls["summary"])
            lines.append("")
        if cls["methods"]:
            lines.append("| Method | Description |")
            lines.append("|---|---|")
            for m in cls["methods"]:
                deco = ""
                if "staticmethod" in m["decorators"]:
                    deco = "*(static)* "
                elif "classmethod" in m["decorators"] or "property" in m["decorators"]:
                    deco = f"*({m['decorators'][0]})* "
                sig = f"`{m['name']}{m['args']}`".replace("|", "\\|")
                lines.append(f"| {deco}{sig} | {escape(m['summary'])} |")
            lines.append("")

    if data["functions"]:
        lines.append("| Function | Description |")
        lines.append("|---|---|")
        for fn in data["functions"]:
            sig = f"`{fn['name']}{fn['args']}`".replace("|", "\\|")
            lines.append(f"| {sig} | {escape(fn['summary'])} |")
        lines.append("")

    return "\n".join(lines)

# Organize datashop_toolbox into logical groups
groups = {
    "ODF Header Classes": [
        "basehdr", "validated_base", "odfhdr", "cruisehdr", "eventhdr",
        "historyhdr", "qualityhdr", "parameterhdr", "instrumenthdr",
        "recordhdr", "records", "polynomialhdr", "generalhdr",
        "compasshdr", "meteohdr",
    ],
    "Instrument & File-Format Utilities": [
        "compare_seabird_xmlcons", "concatenate_qat_files", "fix_btl_header",
        "lookup_parameter", "netcdfhdr", "odf_to_exchange_format",
        "read_seaodf_ini", "read_seaodf_parameters", "rbr_to_odf",
        "remove_parameter",
    ],
    "MTR / Thermograph Processing": [
        "thermograph", "multinet", "process_mtr_files", "ai_thermograph_data",
    ],
    "Quality Control & Reporting": [
        "qc_odf_data", "metadata_report",
    ],
    "GUI Support Widgets": [
        "log_window", "select_metadata_file_and_data_folder",
    ],
    "Package Setup / Entry Scripts": [
        "__init__", "create_parameters_database", "demo_validated_base",
        "generate_metadata_report",
    ],
}

grouped_names = {n for names in groups.values() for n in names}
ungrouped = sorted(set(dt.keys()) - grouped_names)
if ungrouped:
    groups["Other"] = ungrouped

out = []
out.append("## `datashop_toolbox`\n")
for group_name, members in groups.items():
    members = [m for m in members if m in dt]
    if not members:
        continue
    out.append(f"### {group_name}\n")
    for m in members:
        out.append(render_module(m, dt[m], heading_level=4))
    out.append("")

with open("section_datashop_toolbox.md", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

# odf_oracle
out2 = []
out2.append("## `odf_oracle`\n")
oracle_groups = {
    "Connection Management": ["__init__", "database_connection_pool"],
    "Value Conversion Helpers": ["fix_null", "sytm_to_timestamp"],
    "ODF-to-Oracle Loaders": [
        "odf_to_oracle", "cruise_event_to_oracle", "event_comments_to_oracle",
        "instrument_to_oracle", "history_to_oracle", "data_to_oracle",
        "meteo_to_oracle", "meteo_comments_to_oracle",
        "quality_to_oracle", "quality_tests_to_oracle", "quality_comments_to_oracle",
        "compass_cal_to_oracle", "polynomial_cal_to_oracle",
        "general_cal_to_oracle", "general_cal_equation_to_oracle",
        "general_cal_comments_to_oracle",
    ],
    "Entry Scripts": ["load_files_to_odf_archive_db"],
}
grouped_names2 = {n for names in oracle_groups.values() for n in names}
ungrouped2 = sorted(set(oracle.keys()) - grouped_names2)
if ungrouped2:
    oracle_groups["Other"] = ungrouped2
for group_name, members in oracle_groups.items():
    members = [m for m in members if m in oracle]
    if not members:
        continue
    out2.append(f"### {group_name}\n")
    for m in members:
        out2.append(render_module(m, oracle[m], heading_level=4))
    out2.append("")

with open("section_odf_oracle.md", "w", encoding="utf-8") as f:
    f.write("\n".join(out2))

# gui
out3 = []
out3.append("## `datashop_toolbox.gui`\n")
gui_groups = {
    "Package Setup": ["__init__"],
    "ODF Metadata Entry": ["odf_metadata_dialog", "odf_metadata_form"],
    "RBR / RSK Processing": ["rbr_to_odf_mainwindow", "rbr_profile_plot"],
    "Thermograph Processing": ["thermograph_gui_loader"],
    "Examples": ["example_btl_generation"],
}
grouped_names3 = {n for names in gui_groups.values() for n in names}
ungrouped3 = sorted(set(gui.keys()) - grouped_names3)
if ungrouped3:
    gui_groups["Other"] = ungrouped3
for group_name, members in gui_groups.items():
    members = [m for m in members if m in gui]
    if not members:
        continue
    out3.append(f"### {group_name}\n")
    for m in members:
        out3.append(render_module(m, gui[m], heading_level=4))
    out3.append("")

with open("section_gui.md", "w", encoding="utf-8") as f:
    f.write("\n".join(out3))

print("Built sections.")
print("datashop_toolbox modules:", len(dt))
print("odf_oracle modules:", len(oracle))
print("gui modules:", len(gui))
