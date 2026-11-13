---
description: Analyze code dependencies, data types, and return values BEFORE making complex code changes. Use this to prevent type mismatches (e.g., JSON string vs Dict) and serialization errors.
---

1. **Identify the Target**:
   - Clarify which class, function, or variable is the main subject of the change.

2. **Trace Definitions & Imports (Static Analysis)**:
   - Open the file containing the target code.
   - Look at the `imports`. If the target interacts with other custom classes (e.g. `ScopeEX_Data_Unit` in `TestCondition`), you **MUST** find where they are defined.
   - Use `grep_search` or `find_by_name` if the file path is not obvious.
   - Use `view_file` to read the *source code* of these dependencies. **Do not guess what they do based on names.**

3. **Verify Data Types (The "No Assumptions" Rule)**:
   - check the `Dependency`:
     - **Serialization**: Does `to_json` return a `str` or a `dict`? Does `from_dict` expect a `dict`?
     - **Data Structures**: Are attributes initialized in `__init__` (instance) or outside (class)?
     - **Return Values**: What exactly do helper methods return?

4. **Runtime Verification (The "Scratchpad" Rule)**:
   - If static analysis leaves ANY ambiguity (especially with dynamic types or serialization), create a temporary script (e.g., `_debug_types.py`).
   - Import the classes, instantiate a minimal example.
   - Print the `type()` of the data in question (e.g. `print(type(obj.to_json()))`).
   - Run it with `python _debug_types.py`.
   - *Delete the script after verification.*

5. **Plan & Execute**:
   - Only after confirming the "Dependency Chain" matches your mental model, proceed to `replace_file_content`.
