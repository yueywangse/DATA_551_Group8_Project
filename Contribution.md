# Contributing to the Vancouver Crime Dashboard

Thank you for your interest in contributing! 
This project visualizes crime data in Vancouver using Python and an interactive dashboard.  
This document explains how to set up the project, coding standards, and how to submit changes.

---

## How You Can Contribute

- Report bugs or data inconsistencies  
- Suggest new visualizations or dashboard features  
- Improve code quality or performance  
- Add tests  
- Enhance documentation  
- Help with data cleaning/ETL improvements  
- Participate in code reviews  

---

## Getting Started

### 1. Fork and Clone the Repository
```bash
git clone https://github.com/yueywangse/DATA_551_Group8_Project.git
cd DATA_551_Group8_Project
```

### 2. Create a Virtual Environment
Using `venv`:
```bash
python3 -m venv .venv
source .venv/bin/activate     # Mac/Linux
.\.venv\Scripts\activate      # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Dashboard

```bash
streamlit run app.py
```
or
```bash
python app.py
```

---

## Project Structure

```
project/
├── app.py                  # dashboard entry point
├── src/
│   ├── data/               # data loading & cleaning
│   ├── visuals/            # plots, maps, charts
│   ├── utils/              # helper functions
│   └── __init__.py
├── data/
│   ├── raw/                # unprocessed data (ignored by Git)
│   └── processed/          # cleaned datasets
├── tests/                  # pytest suite
├── docs/                   # documentation
├── requirements.txt
├── CONTRIBUTING.md
└── README.md
```

> **Note:** Do not commit large data files or anything containing sensitive information.

---

## Environment Variables

If you need API keys (e.g., Mapbox tiles), create a local `.env` file:

```
cp .env.example .env
```

Never commit `.env`.

---

## Coding Guidelines

### Code Style
Please follow these conventions:

- Write clear, descriptive variable names  
- Include docstrings for functions and modules  
- Prefer small, modular functions over large blocks of logic  

## Testing

We use **pytest**.

Run tests with:
```bash
pytest
```

Add tests for any new functionality, especially:

- data transformations  
- visualization preparation functions  
- utility methods  

---

## Data Pipeline Guidelines

When adding or modifying data-processing code:

- Validate input columns  
- Clean null or inconsistent values  
- Use clear, deterministic transformations  
- Log transformation steps where useful  
- Save cleaned data to `data/processed/`  
- Document any assumptions in `docs/data-sources.md`  

---

## Pull Request Process

Before submitting a PR, make sure to:

- [ ] Run formatters and linters  
- [ ] Add/update tests  
- [ ] Ensure all tests pass  
- [ ] Update documentation where needed  
- [ ] Attach screenshots for UI-related changes  

Include a clear explanation:

- What you changed  
- Why the change is needed  
- How to test it  
- Any considerations (performance, data behavior, etc.)  

---

## Reporting Bugs

When opening an issue, include:

- Steps to reproduce  
- Expected vs actual behavior  
- Error messages or logs  
- Data files or snippets (if small)  
- Your OS and Python version  

---

## Suggesting Features

Please include:

- The problem the feature solves  
- Proposed solution  
- Possible alternatives  
- Mockups or example visuals (optional)  

---

## Code of Conduct

All participants are expected to follow our `CODE_OF_CONDUCT.md`.

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see `LICENSE`).

---

## Thank You!

We appreciate your help in improving this project and making Vancouver crime data more accessible and understandable!