#!/usr/bin/env python

"""Report state based on FAUCET/Gauge/Prometheus variables."""

# TODO: this script and is usage is experimental and its output
# is expected to change significantly.
# TODO: add control functionality.

# Copyright (C) 2015 Brad Cowie, Christopher Lorier and Joe Stringer.
# Copyright (C) 2015 Research and Education Advanced Network New Zealand Ltd.
# Copyright (C) 2015--2017 The Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pytype: disable=pyi-error
# pytype: disable=import-error
import getopt
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import requests
from prometheus_client import parser

# TODO: byte/packet counters could be per second (given multiple samples)
def decode_value(metric_name, value):
    """Convert values to human readible format based on metric name"""
    result = value
    if metric_name == 'learned_macs':
        result = ':'.join(
            format(octet, '02x') for octet in int(value).to_bytes( # pytype: disable=attribute-error
                6, byteorder='big')
            )
    return result

def scrape_prometheus(endpoints, retries=3):
    """Scrape a list of Prometheus/FAUCET/Gauge endpoints and aggregate results."""
    metrics = []
    for endpoint in endpoints:
        content = None
        err = None
        for _ in range(retries):
            try:
                if endpoint.startswith('http'):
                    response = requests.get(endpoint)
                    if response.status_code == requests.status_codes.codes.ok: # pylint: disable=no-member
                        content = response.content.decode('utf-8', 'strict')
                        break
                else:
                    response = urllib.request.urlopen(endpoint) # pytype: disable=module-attr
                    content = response.read().decode('utf-8', 'strict')
                    break
            except requests.exceptions.ConnectionError as exception:
                err = exception
                time.sleep(1)
        if err is not None:
            print(err)
            return None
        endpoint_metrics = parser.text_string_to_metric_families(
            content)
        metrics.extend(endpoint_metrics)
    return metrics

def report_label_match_metrics(report_metrics, metrics, display_labels=None,
                               nonzero_only=False, delim='\t', label_matches=None):
    """Text report on a list of Prometheus metrics."""
    report_output = []
    for metric in metrics:
        if not report_metrics or metric.name in report_metrics:
            for _, labels, value in metric.samples:
                if (label_matches is None or
                        (label_matches and set(
                            label_matches.items()).issubset(set(labels.items())))):
                    if nonzero_only and int(value) == 0:
                        continue

                    sorted_labels = []
                    for key, val in sorted(labels.items()):
                        if not display_labels or key in display_labels:
                            sorted_labels.append((key, val))
                    value = decode_value(metric.name, value)
                    report_output.append(
                        delim.join((metric.name, str(sorted_labels), str(value)))
                        )
    report_output = '\n'.join(report_output)
    return report_output


def usage():
    """print usage and exit with -1"""
    usage_vars = {'self': sys.argv[0]}
    print(("""
Retrieve FAUCET/Gauge state using Prometheus variables.

    {self} [-n] <-e|--endpoints=http://server:port> [-m|--metrics=prometheus_metrics,] [-l|--labels=name:value,]

    -n: Don't report 0 values
    -e|--endpoints: list of Prometheus endpoints to query (comma separated)
    -m|--metrics: list of Prometheus variables to query (comma separated)
    -l|--labels: filter list of Prometheus variables by labels that must be present (comma separated)
    --display-labels: list of labels to display with the results (comma separated). By default display all labels.

Examples:

    MACs learned on a DP.

    {self} -n --endpoints=http://172.17.0.1:9302 --metrics=learned_macs --labels=dp_id:0xb827eb608918

    Status of all DPs

    {self} -n --endpoints=http://172.17.0.1:9302 --metrics=dp_status
""".format(**usage_vars))) # pytype: disable=duplicate-keyword-argument
    sys.exit(-1)


def parse_args(sys_args):
    """Parse and return CLI args."""
    try:
        opts, _ = getopt.getopt(
            sys_args,
            'ne:m:l:',
            ['nonzero', 'endpoints=', 'metrics=', 'labels=', 'display-labels=']
            )
    except getopt.GetoptError:
        usage()

    endpoints = []
    report_metrics = []
    label_matches = None
    display_labels = None
    nonzero_only = False

    for opt, arg in opts:
        if opt in ('-n', '--nonzero'):
            nonzero_only = True
        elif opt == '--display-labels':
            display_labels = arg.split(',')
        elif opt in ('-e', '--endpoints'):
            endpoints = arg.split(',')
        elif opt in ('-m', '--metrics'):
            report_metrics = arg.split(',')
        elif opt in ('-l', '--labels'):
            for label_value in arg.split(','):
                label, value = label_value.split(':')
                if label_matches is None:
                    label_matches = {}
                label_matches[label] = value
        else:
            usage()

    return (endpoints, report_metrics, label_matches, nonzero_only, display_labels)


def main():
    (
        endpoints,
        report_metrics,
        label_matches,
        nonzero_only,
        display_labels
        ) = parse_args(sys.argv[1:])
    metrics = scrape_prometheus(endpoints)
    if metrics is None:
        sys.exit(1)
    print(report_label_match_metrics(
        report_metrics,
        metrics,
        nonzero_only=nonzero_only,
        label_matches=label_matches,
        display_labels=display_labels
        ))


if __name__ == '__main__':
    main()
