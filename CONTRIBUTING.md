# Contribution Guidelines

Thank you for your interest in contributing to [dwave-examples](https://github.com/dwave-examples)!
Before getting started, we encourage you to take a look at the following guidelines.

## What We're Looking For

While we have a preference for application-oriented examples, we welcome all examples that
demonstrate use of Ocean&trade; SDK tools.

To see examples of what we are looking for, you can view our existing demos by either creating a
free account on the [Leap&trade; Quantum Cloud Service](https://cloud.dwavesys.com/leap/signup/)
and browsing our categorized [library of examples](https://cloud.dwavesys.com/leap/examples/) or by
reading through the demo code repositories in [dwave-examples](https://github.com/dwave-examples).

## Steps for Contributing

1.  Follow GitHub's instructions for
    [creating a repository from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).
    Alternatively, clone this repository as a starting point from which to implement your example.

2.  Implement your example by following these instructions:

    1.  It is preferable for you to write all Python and CSS code in either new files or files that
        contain `demo` in the name. Below is a list of `demo` files and their functionality:

        *   [demo_callbacks.py](demo_callbacks.py) contains all the
            [Dash callback functions](https://dash.plotly.com/basic-callbacks) required to run the
            Dash app. Updates to existing callbacks and new callbacks should be made in this file.
        *   [demo_interface.py](demo_interface.py) contains all the Dash HTML components that
            generate the user interface (UI) for the app, including settings like sliders,
            checkboxes, and text inputs, as well as buttons and tables. If a Dash HTML component
            needs to be dynamically added to the UI by a Dash callback in `demo_callbacks.py`, it
            is encouraged to add a function generating this component to `demo_interface.py` and
            call this function from `demo_callbacks.py`.
        *   [demo_configs.py](demo_configs.py) contains all configurations and settings for the
            demo and is intended as a quick way to customize the demo for a specific audience or
            use case. Add variables to this file that users may want to change; for example, titles
            and default settings values but not evergreen labels or internal variables.
        *   [demo.css](assets/demo.css) contains all custom CSS styling for the demo; any new CSS rules
            should be added here or in a new file in the `/assets/` directory. Dash reads all
            files in `/assets/` in alphabetical order so, out of the provided CSS files, `demo.css`
            runs last and can overwrite previous styling rules.
        *   [__demo_variables.css](assets/__demo_variables.css) contains all CSS variables.
            It is encouraged to edit or add more CSS variables here.
        *   [demo_enums.py](src/demo_enums.py) contains [Enum](https://docs.python.org/3/library/enum.html)
            classes for any settings or variables that are being used frequently to avoid string
            comparisons or other fragile code practices.

    2.  All new files should be added to one of the following directories:
        *   `/assets/` is a Dash-specific directory that must not contain subdirectories and must
            not be renamed. Dash always reads files in this directory in alphabetical order and
            therefore you do not need to explicitly import files from this directory. Avoid altering
            CSS files with the word `demo` in the filename.
        *   `/src/` should contain all functional code for the demo including solver implementations,
            class definitions, etc. You can add subdirectories as needed.
        *   `/static/` should contain all new static files such as images. You can add subdirectories
            as needed.
        *   `/tests/` should contain tests for all code found in `/src/`. All tests should be
            discoverable through `python -m unittest discover`.

    3.  Follow the [README template](README.md) to create a README that describes your example and
        outlines how it works.

3.  Once your example has been implemented,
    [open an issue](https://github.com/dwave-examples/template-dash/issues/new/choose) in the
    [dwave-examples/template-dash](https://github.com/dwave-examples/template-dash) repository
    with a link to your example.

When adding a contributed example, D-Wave forks your repository and may make a pull 
request to get your approval for certain code changes.

## Final Checklist

- [ ] **PEP 8**: All code follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
If you are unsure, install and run [black](https://pypi.org/project/black/) to ensure correct formatting.

- [ ] **AI Disclosure**: You must disclose whether AI has been used to assist in the development of
your pull request. You must document which tool(s) have been used, how they were used, and specify
what code or text is AI generated. We will reject any pull request that does not include the
disclosure. See full policy [here](https://docs.dwavequantum.com/en/latest/ocean/ai_policy.html).

- [ ] **Docstrings**: All functions contain docstrings describing what the function does and any
arguments or return values. For more information, see the
[Google docstrings convention](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

- [ ] **README**: The demo contains an updated `README.md` file that follows the
[README template](README.md) and is written in Markdown.

- [ ] **Requirements**: All requirements for running the demo have been listed in `requirements.txt`
and are either pinned to a version supported by the latest Ocean SDK release or lower bounded.
`dwave-ocean-sdk` version specified has to be compatible with the latest release available.

- [ ] **LICENSE**: The demo complies with the Apache 2.0 License and the [`LICENSE`](LICENSE) file
is included in the root directory. All files include a license header.

- [ ] **Tests**: All code included in the `/src/` directory has associated tests that are located in
`/tests/` and discoverable through `python -m unittest discover`.

- [ ] **Accessibility**: The demo must be tested for accessibility standards and score at least
80%. The base template provided scores 100%.

- [ ] **Codespaces**: The [`.devcontainer/`](.devcontainer/) directory is included in the demo's
root directory to ensure the demo runs in
[GitHub Codespaces](https://docs.github.com/en/codespaces/overview).

- [ ] **CircleCI**: The demo contains the [`.circleci/`](.circleci/) directory to support running
tests in CI. Once approved, we will make sure that your example is set up on our CircleCI account.

> [!NOTE]\
> Our examples are tested using CircleCI. For a list of operating systems and
Python versions we currently test our examples with, please take a look at [our
documentation](https://docs.ocean.dwavesys.com/en/stable/overview/install.html).
For more information, visit [orb-examples](https://circleci.com/developer/orbs/orb/dwave/orb-examples).

---

For more information about contributing, take a look at our
[How to Contribute](https://docs.ocean.dwavesys.com/en/latest/contributing.html#documentation-and-comments)
guide.
