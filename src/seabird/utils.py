import os
import re
from importlib import resources
import logging
import json

# import codecs

from seabird.exceptions import CNVError

module_logger = logging.getLogger("seabird.utils")


def make_file_list(inputdir, inputpattern=r".*\.cnv"):
    """Search inputdir recursively for inputpattern"""
    inputfiles = []
    for dirpath, dirnames, filenames in os.walk(inputdir):
        for filename in filenames:
            if re.match(inputpattern, filename):
                inputfiles.append(os.path.join(dirpath, filename))
    inputfiles.sort()
    return inputfiles


def basic_logger(logger=None):
    if logger is not None:
        assert type(logger) is logging.Logger
    else:
        # create logger
        logger = logging.getLogger("CNV logger")
        logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(ch)

    return logger


def press2depth(press, latitude):
    """calculate depth from pressure
    http://www.seabird.com/application_notes/AN69.htm

    ATENTION, move it to fluid.
    """
    import numpy as np

    x = np.sin((np.pi / 180) * latitude / 57.29578) ** 2
    g = 9.780318 * (1.0 + (5.2788e-3 + 2.36e-5 * x) * x) + 1.092e-6 * press
    depth = (
        -(
            (((-1.82e-15 * press + 2.279e-10) * press - 2.2512e-5) * press + 9.72659)
            * press
        )
        / g
    )
    return depth


def load_rule(raw_text):
    """Load the adequate rules to parse the data.

    Tries all available CNV rules bundled with the seabird package
    and returns the first rule that successfully parses the input.
    """

    try:
        rules_root = resources.files("seabird").joinpath("rules")
    except (ModuleNotFoundError, FileNotFoundError):
        raise CNVError(tag="noparsingrule")

    rule_files = sorted(
        p for p in rules_root.iterdir()
        if p.name.startswith("cnv") and p.name.endswith(".json")
    )

    for rule_path in rule_files:
        rule = json.loads(rule_path.read_text(encoding="utf-8"))

        # Build the parsing regex
        if "sep" in rule:
            regex = rule["header"] + rule["sep"] + rule["data"]
        else:
            regex = (
                "(?P<header>" + rule["header"] + ")"
                "(?P<data>(?:" + rule["data"] + ")+)"
            )

        content_re = re.compile(regex, re.VERBOSE)

        match = content_re.search(raw_text)
        if match:
            return rule, match.groupdict()

    # No rule matched
    raise CNVError(tag="noparsingrule")


def seabird_dir(subdir=None):
    """Return the local support/config directory

    Returns a local directory used to store testing data. The default path
     (~/.config/seabird) can be overwritten by the environment variable
     SEABIRD_DIR.
    """
    spath = os.getenv("SEABIRD_DIR", "~/.config/seabird")
    return os.path.expanduser(spath).replace("/", os.path.sep)


def sampledata(filename=None, dtype=None):
    """Return the full path to local sample data

    The first time it will download the sample data files into the default
      seabird directory. Check seabird_dir() if you want to modify that.
    """
    try:
        from supportdata import download_file
    except ImportError:
        module_logger.error(
            "Missing package supportdata. Try:\npip install supportdata"
        )

    outputdir = os.path.join(seabird_dir(), "sampledata")
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    src = "https://raw.githubusercontent.com/castelao/seabird/dev/sampledata"

    filesdb = {
        "PIRA001.cnv": {"dtype": "CTD", "md5": "5ded777144300b63c8775b1d7f033f92"},
        "dPIRX003.cnv": {"dtype": "CTD", "md5": "4b941b902a3aea7d99e1cf4c78c51877"},
        "dPIRX010.cnv": {"dtype": "CTD", "md5": "8691409accb534c83c8bd412afbdd285"},
        "Hotin.cnv": {"dtype": "CTD", "md5": "814dc769c0775327bbe5b0f489dfb571"},
        "missing_whitespace.cnv": {
            "dtype": "CTD",
            "md5": "c1f00cebb5f00f6aaebc316bac3fd86a",
        },
        "SK287_CTD05.cnv": {"dtype": "CTD", "md5": "08e974c46ed603442eecf9145031a6c4"},
        "sta0860.cnv": {"dtype": "CTD", "md5": "1c788c4d9b82b527ebf0c2fb9200600e"},
        #'more_after_file_type.cnv': {
        #    'dtype': "CTD", 'md5': "e5bffcfdcaf52333773bbe7abe98b06d"},
        # ['CTD', 'laurynas.cnv', '6f188d53ac2d7aaaf4ce69c0e5c514ec'],
        # 'TSG_PIR_001.cnv': {
        #    'dtype': "TSG", 'md5': "2950ccb9f77e0802557b011c63d2e39b"},
        # 'TSG_PIR_010.cnv': {
        #    'dtype': "TSG", 'md5': "d87cea33bfe37e22dc8e563f77cbf307"},
        # 'MI18MHDR.btl': {
        #     'dtype': "btl", 'md5': "775f2a6c6585f1cffb0038111580e5a1"},
    }

    if dtype is not None:
        for f in [f for f in filesdb if filesdb[f]["dtype"] != dtype]:
            del filesdb[f]

    if filename is None:
        datafile = []
        for f in filesdb:
            print(f)
            download_file(
                outputdir=outputdir,
                url=os.path.join(src, filesdb[f]["dtype"], f),
                filename=f,
                md5hash=filesdb[f]["md5"],
            )
            datafile.append(os.path.join(outputdir, f))
        return datafile

    elif filename in filesdb:
        download_file(
            outputdir=outputdir,
            url=os.path.join(src, filesdb[filename]["dtype"], filename),
            filename=filename,
            md5hash=filesdb[filename]["md5"],
        )
        return os.path.join(outputdir, filename)

    else:
        module_logger.error("%s is not a valid test file" % filename)
