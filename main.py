from collections import defaultdict
from dataclasses import dataclass
from dataclasses_json import Undefined, dataclass_json
from datetime import datetime
from dateutil import parser
from marshmallow import fields
from typing import Optional
from urllib.parse import urlencode
import argparse
import dataclasses_json
import json
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests
import plotly.graph_objects as go

dataclasses_json.cfg.global_config.encoders[datetime] = datetime.isoformat
dataclasses_json.cfg.global_config.decoders[datetime] = parser.isoparse
dataclasses_json.cfg.global_config.mm_fields[datetime] = fields.DateTime(format="iso")


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Config:
    host: str
    project_id: int


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Issue:
    iid: int
    created_at: datetime
    closed_at: datetime | str | type(None) = None


def get_issues(config: Config, params):
    results = []
    for i in range(1, 101):
        # https://docs.gitlab.com/ee/api/rest/index.html#offset-based-pagination
        page_params = {"page": i, "per_page": 100}
        page_params.update(params)
        # https://docs.gitlab.com/ee/api/issues.html#list-issues
        url = f"{config.host}/api/v4/projects/{config.project_id}/issues?{urlencode(page_params)}"
        response = requests.get(url).json()
        if len(response) == 0:
            break
        results.append(response)
    return [issue for result in results for issue in result]


def create_burndown_chart(start, end, weights):
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.axis((start, end, 0, weights[0]))
    plt.setp(ax.get_xticklabels(), rotation=15)
    ax.plot((start, end), (weights[0], 0))
    ax.plot(*weights[2], marker="o")
    plt.savefig("output.png")


def get_burndown_coords(issues: list[Issue], html: str):
    df_created = pd.to_datetime(
        pd.DataFrame(
            {
                "issues": [issue.created_at for issue in issues]
                + [issue.closed_at for issue in issues if issue.closed_at != None]
            }
        )["issues"]
    )
    created_at_min = df_created.min().date()
    created_at_max = df_created.max().date()

    df_issues = pd.DataFrame(index=pd.date_range(created_at_min, created_at_max))

    df_issues["created_count"] = 0
    df_issues["closed_count"] = 0
    for issue in issues:
        if issue.closed_at != None:
            df_issues.at[
                pd.Timestamp(pd.Timestamp(issue.closed_at).date()), "closed_count"
            ] += 1
        df_issues.at[
            pd.Timestamp(pd.Timestamp(issue.created_at).date()), "created_count"
        ] += 1

    df_issues["created_count"] = df_issues["created_count"].cumsum()
    df_issues["closed_count"] = df_issues["closed_count"].cumsum()

    df_issues["remaining_count"] = (
        df_issues["created_count"] - df_issues["closed_count"]
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_issues.index,
            y=df_issues["remaining_count"],
            line_shape="spline",
            name="Remaining",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_issues.index,
            y=df_issues["created_count"],
            line_shape="spline",
            name="Total created",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_issues.index,
            y=df_issues["closed_count"],
            line_shape="spline",
            name="Total closed",
        )
    )
    fig.update_traces(mode="markers+lines", hovertemplate=None)
    fig.update_layout(xaxis_title="Date", yaxis_title="Issues", hovermode="x")
    fig.write_html(html)


def run():
    parser = argparse.ArgumentParser(
        description="Generate a burndown diagram for a GitLab repository"
    )
    parser.add_argument(
        "--config", type=str, help="Path to config", default="config.json"
    )
    parser.add_argument("--host", type=str, help="GitLab host. Overrides config value")
    parser.add_argument(
        "--project-id", type=str, help="Project ID. Overrides config value"
    )
    parser.add_argument("--fetch", action="store_true", help="Fetch GitLab data")
    parser.add_argument(
        "--json",
        type=str,
        help="Path to a file with issues data",
        default="issues.json",
    )
    parser.add_argument(
        "--html",
        type=str,
        help="Path to a file with an interactive diagram",
        default="index.html",
    )
    # TODO query parameters?
    args = parser.parse_args()

    if args.fetch:
        config_raw = {}
        if args.config != None:
            with open(args.config, "r") as f:
                config_raw = json.load(f)

        if args.host != None:
            config_raw.update("host", args.host)

        if args.project_id != None:
            config_raw.update("id", args.project_id)

        config = Config.schema().load(config_raw)

        issues_json = get_issues(config, {"scope": "all"})
        issues = Issue.schema().load(issues_json, many=True)

        with open(args.json, "w") as f:
            f.write(Issue.schema().dumps(issues, many=True, indent=4))
    else:
        with open(args.json, "r") as f:
            issues_json = json.load(f)
            issues = Issue.schema().load(issues_json, many=True)

    get_burndown_coords(issues, html=args.html)


if __name__ == "__main__":
    run()
