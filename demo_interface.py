# Copyright 2024 D-Wave
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This file stores the Dash HTML layout for the app."""
from __future__ import annotations
from enum import EnumMeta

from dash import dcc, html
import dash_mantine_components as dmc

from demo_configs import (
    CHECKLIST,
    DESCRIPTION,
    DROPDOWN,
    MAIN_HEADER,
    RADIO,
    SLIDER,
    SOLVER_TIME,
    THUMBNAIL,
)
from src.demo_enums import SolverType

THEME_COLOR = "#2d4376"


def slider(label: str, id: str, config: dict) -> html.Div:
    """Slider element for value selection.

    Args:
        label: The title that goes above the slider.
        id: A unique selector for this element.
        config: A dictionary of slider configurations, see dmc.Slider Dash Mantine docs.
    """
    return html.Div(
        className="slider-wrapper",
        children=[
            html.Label(label, htmlFor=id),
            dmc.Slider(
                id=id,
                className="slider",
                **config,
                marks=[
                    {"value": config["min"], "label": f'{config["min"]}'},
                    {"value": config["max"], "label": f'{config["max"]}'},
                ],
                labelAlwaysOn=True,
                thumbLabel=f"{label} slider",
                color=THEME_COLOR,
            ),
        ],
    )


def range_slider(label: str, id: str, config: dict) -> html.Div:
    """Range slider element for value selection.

    Args:
        label: The title that goes above the range slider.
        id: A unique selector for this element.
        config: A dictionary of range slider configurations, see dmc.RangeSlider Dash Mantine docs.
    """
    return html.Div(
        className="rangeslider-wrapper",
        children=[
            html.Label(label, htmlFor=id),
            dmc.RangeSlider(
                id=id,
                className="slider",
                **config,
                marks=[
                    {"value": config["min"], "label": f'{config["min"]}'},
                    {"value": config["max"], "label": f'{config["max"]}'},
                ],
                labelAlwaysOn=True,
                thumbFromLabel=f"{label} slider start",
                thumbToLabel=f"{label} slider end",
                color=THEME_COLOR,
            )
        ]
    )


def dropdown(label: str, id: str, options: list) -> html.Div:
    """Dropdown element for option selection.

    Args:
        label: The title that goes above the dropdown.
        id: A unique selector for this element.
        options: A list of dictionaries of labels and values.
    """
    return html.Div(
        className="dropdown-wrapper",
        children=[
            html.Label(label, htmlFor=id),
            dmc.Select(
                id=id,
                data=options,
                value=options[0]["value"],
                allowDeselect=False,
            ),
        ],
    )


def checklist(label: str, id: str, options: list, values: list, inline: bool = True) -> html.Div:
    """Checklist element for option selection.

    Args:
        label: The title that goes above the checklist.
        id: A unique selector for this element.
        options: A list of dictionaries of labels and values.
        values: A list of values that should be preselected in the checklist.
        inline: Whether the options of the checklist are displayed beside or below each other.
    """
    return html.Div(
        className="checklist-wrapper",
        children=[
            dmc.CheckboxGroup(
                id=id,
                className=f"checklist{' checklist--inline' if inline else ''}",
                label=label,
                value=values,
                children=dmc.Group(
                    [
                        dmc.Checkbox(label=option["label"], value=option["value"], color=THEME_COLOR)
                        for option in options
                    ],
                ),
            ),
        ],
    )


def checkbox(label: str, id: str, checked: bool) -> html.Div:
    """Checkbox element.

    Args:
        label: The title that goes above the checkbox.
        id: A unique selector for this element.
        checked: Whether the checkbox is checked or not.
    """
    return html.Div(
        className="checkbox-wrapper",
        children=[
            dmc.Checkbox(
                id=id,
                label=label,
                checked=checked,
                color=THEME_COLOR,
            )
        ],
    )


def radio(label: str, id: str, options: list, value: str, inline: bool = True) -> html.Div:
    """Radio element for option selection.

    Args:
        label: The title that goes above the radio.
        id: A unique selector for this element.
        options: A list of dictionaries of labels and values.
        value: The value of the radio that should be preselected.
        inline: Whether the options are displayed beside or below each other.
    """
    return html.Div(
        className="radio-wrapper",
        children=[
            dmc.RadioGroup(
                id=id,
                className=f"radio{' radio--inline' if inline else ''}",
                label=label,
                value=value,
                children=dmc.Group(
                    [
                        dmc.Radio(option["label"], value=option["value"], color=THEME_COLOR)
                        for option in options
                    ]
                ),
            ),
        ],
    )


def input(label: str, id: str, configs: dict, type: str="number") -> html.Div:
    """Input element for either text or number input.

    Args:
        label: The title that goes above the input.
        id: A unique selector for this element.
        configs: A dictionary of configurations for the input element.
        type: The type of input, either "number" or "text".
    """
    return html.Div(
        className="input-wrapper",
        children=[
            html.Label(label, htmlFor=id),
            dmc.TextInput(
                id=id,
                **configs,
            ) if type == "text" else dmc.NumberInput(
                id=id,
                **configs,
            ),
        ],
    )


def generate_options(options: list | EnumMeta | dict) -> list[dict]:
    """Format options for dropdowns, checklists, radios, etc.

    Args:
        options: A list, EnumMeta, or dictionary of options to format.

    Returns:
        A list of dictionaries with "label" and "value" keys for each option.
    """
    if isinstance(options, EnumMeta):
        return [{"label": option.label, "value": f"{option.value}"} for option in options]

    if isinstance(options, dict):
        return [{"label": f"{key}", "value": f"{value}"} for key, value in options.items()]

    return [{"label": f"{option}", "value": f"{option}"} for option in options]


def generate_settings_form() -> html.Div:
    """Generate settings for selecting the scenario, model, and solver.

    Returns:
        A Div containing the settings for selecting the scenario, model, and solver.
    """
    dropdown_options = generate_options(DROPDOWN)
    checklist_options = generate_options(CHECKLIST)
    radio_options = generate_options(RADIO)
    solver_options = generate_options(SolverType)

    return html.Div(
        className="settings",
        children=[
            slider(
                "Example Slider",
                "slider",
                SLIDER,
            ),
            dropdown(
                "Example Dropdown",
                "dropdown",
                sorted(dropdown_options, key=lambda op: op["value"]),
            ),
            checklist(
                "Example Checklist",
                "checklist",
                sorted(checklist_options, key=lambda op: op["value"]),
                [checklist_options[0]["value"]],
            ),
            radio(
                "Example Radio",
                "radio",
                sorted(radio_options, key=lambda op: op["value"]),
                radio_options[0]["value"],
            ),
            dropdown(
                "Solver",
                "solver-type-select",
                sorted(solver_options, key=lambda op: op["value"]),
            ),
            input(
                "Solver Time Limit (seconds)",
                "solver-time-limit",
                SOLVER_TIME,
            ),
        ],
    )


def generate_run_buttons() -> html.Div:
    """Generate run and cancel buttons to run the optimization."""
    return html.Div(
        id="button-group",
        children=[
            html.Button("Run Optimization", id="run-button", className="button"),
            html.Button(
                "Cancel Optimization",
                id="cancel-button",
                className="button",
                style={"display": "none"},
            ),
        ],
    )


def generate_table(table_data: dict[str, list]) -> html.Table:
    """Generate a table containing table_data.

    Args:
        table_data: A dictionary of table header keys and table column values.

    Returns:
        An HTML table containing table_data.
    """
    table_columns = table_data.values()
    num_rows = len(next(iter(table_columns)))

    return html.Table(
        className="problem-details-table",
        children=[
            html.Thead(html.Tr([html.Th(table_header) for table_header in table_data.keys()])),
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Td(column[i]) for column in table_columns
                        ]
                    ) for i in range(num_rows)
                ]
            ),
        ],
    )


def problem_details(index: int) -> html.Div:
    """Generate the problem details section.

    Args:
        index: Unique element id to differentiate matching elements. Must be different from left
            column collapse button.

    Returns:
        Div containing a collapsable table.
    """
    return html.Div(
        id={"type": "to-collapse-class", "index": index},
        className="details-collapse-wrapper collapsed",
        children=[
            # Problem details collapsible button and header
            html.Button(
                id={"type": "collapse-trigger", "index": index},
                className="details-collapse",
                children=[
                    html.H5("Problem Details"),
                    html.Div(className="collapse-arrow"),
                ],
                **{"aria-expanded": "true"},
            ),
            html.Div(
                className="details-to-collapse",
                id="problem-details",
            ),
        ],
    )


def create_interface() -> html.Div:
    """Create the main application interface."""
    return html.Div(
        id="app-container",
        children=[
            html.A(  # Skip link for accessibility
                "Skip to main content",
                href="#main-content",
                id="skip-to-main",
                className="skip-link",
                tabIndex=1,
            ),
            # Below are any temporary storage items, e.g., for sharing data between callbacks.
            dcc.Store(id="run-in-progress", data=False),  # Indicates whether run is in progress
            # Settings and results columns
            html.Main(
                className="columns-main",
                id="main-content",
                children=[
                    # Left column
                    html.Div(
                        id={"type": "to-collapse-class", "index": 0},
                        className="left-column",
                        children=[
                            html.Div(
                                className="left-column-layer-1",  # Fixed width Div to collapse
                                children=[
                                    html.Div(
                                        className="left-column-layer-2",  # Padding and content wrapper
                                        children=[
                                            html.Div(
                                                [
                                                    html.H1(MAIN_HEADER),
                                                    html.P(DESCRIPTION),
                                                ],
                                                className="title-section",
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        html.Div(
                                                            [
                                                                generate_settings_form(),
                                                                generate_run_buttons(),
                                                            ],
                                                            className="settings-and-buttons",
                                                        ),
                                                        className="settings-and-buttons-wrapper",
                                                    ),
                                                    # Left column collapse button
                                                    html.Div(
                                                        html.Button(
                                                            id={
                                                                "type": "collapse-trigger",
                                                                "index": 0,
                                                            },
                                                            className="left-column-collapse",
                                                            title="Collapse sidebar",
                                                            children=[
                                                                html.Div(className="collapse-arrow")
                                                            ],
                                                            **{"aria-expanded": "true"},
                                                        ),
                                                    ),
                                                ],
                                                className="form-section",
                                            ),
                                        ],
                                    )
                                ],
                            ),
                        ],
                    ),
                    # Right column
                    html.Div(
                        className="right-column",
                        children=[
                            dmc.Tabs(
                                id="tabs",
                                value="input-tab",
                                color="white",
                                children=[
                                    html.Header(
                                        className="banner",
                                        children=[
                                            html.Nav(
                                                [
                                                    dmc.TabsList(
                                                        [
                                                            dmc.TabsTab("Input", value="input-tab"),
                                                            dmc.TabsTab(
                                                                "Results",
                                                                value="results-tab",
                                                                id="results-tab",
                                                                disabled=True,
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            ),
                                            html.Img(src=THUMBNAIL, alt="D-Wave logo"),
                                        ],
                                    ),
                                    dmc.TabsPanel(
                                        value="input-tab",
                                        tabIndex="12",
                                        children=[
                                            html.Div(
                                                className="tab-content-wrapper",
                                                children=[
                                                    dcc.Loading(
                                                        parent_className="input",
                                                        type="circle",
                                                        color=THEME_COLOR,
                                                        # A Dash callback (in app.py) will generate content in the Div below
                                                        children=html.Div(id="input"),
                                                    ),
                                                ]
                                            )
                                        ],
                                    ),
                                    dmc.TabsPanel(
                                        value="results-tab",
                                        tabIndex="13",
                                        children=[
                                            html.Div(
                                                className="tab-content-wrapper",
                                                children=[
                                                    dcc.Loading(
                                                        parent_className="results",
                                                        type="circle",
                                                        color=THEME_COLOR,
                                                        # A Dash callback (in app.py) will generate content in the Div below
                                                        children=html.Div(id="results"),
                                                    ),
                                                    # Problem details dropdown
                                                    html.Div([html.Hr(), problem_details(1)]),
                                                ],
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ],
    )
