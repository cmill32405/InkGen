# Code Review Report - InkGen Repository

## Summary
This report documents coding issues, legacy code, and missing documentation found during a thorough review of the InkGen repository.

## Issues Fixed

### 1. Coding Issues in `boundary.py`
- ✅ **Fixed**: Duplicate docstring on lines 16-17
- ✅ **Fixed**: Typo "argumen" → "argument" on line 21
- ✅ **Fixed**: Duplicate assignment of `self._outer` (lines 18 and 23)
- ✅ **Fixed**: Added docstring to `_hull_check()` method
- ✅ **Fixed**: Improved return type hints for `create_from_dict()` methods

### 2. Legacy Code Removed
- ✅ **Removed**: Standalone `_normalize_padding()` function in `table.py` (lines 271-278) - this was duplicate code as the method already exists in the `Table` class

### 3. Documentation Improvements
- ✅ **Added**: Docstrings to helper functions in `text_outline.py`:
  - `_px_to_units()`
  - `sample_path_points()`
  - `_shape_with_harfbuzz()`
  - `_glyphs_to_svg_path()`
  - `_sample_svg_path()`
- ✅ **Added**: Improved docstring for `_coerce_command_points()` in `svg_generator.py`
- ✅ **Removed**: Commented-out import in `document.py` (`#import YAML`)

## Issues Remaining

### 1. Type Hints - Return Types
Many methods return `object` instead of specific types. These should be updated:

**Files with `-> object` return types:**
- `src/InkGen/component.py`: 15+ methods
- `src/InkGen/svg_generator.py`: 9 methods
- `src/InkGen/document.py`: 2 methods
- `src/InkGen/cad_component_groups.py`: 1 method

**Example fixes needed:**
```python
# Current:
@classmethod
def create_from_dict(cls, data: dict) -> object:

# Should be:
@classmethod
def create_from_dict(cls, data: dict) -> "Component":
```

### 2. Missing Docstrings
Several methods and properties lack docstrings:

**In `style.py`:**
- `Style.create_from_dict()` - returns `None` instead of `Style` (also a type hint issue)
- `DrawingStyle.create_from_dict()` - returns `None` instead of `DrawingStyle`
- `Font.create_from_dict()` - returns `None` instead of `Font`
- `TextStyle.create_from_dict()` - returns `None` instead of `TextStyle`
- Various setter methods lack docstrings

**In `table.py`:**
- Several setter methods lack docstrings
- `Row`, `Column`, and `Cell` classes have minimal docstrings

**In `component.py`:**
- Many `create_from_dict()` methods return `object` and could use better type hints
- Some private methods lack docstrings

### 3. Linting Issues in Examples
**File: `examples/run_inkgen_primitives.py`**
- 18 line length violations (lines exceed 79 characters)
- 1 unused variable: `ymin` on line 62
- 6 instances of accessing protected members (`_canvas`, `_mask_override`)
- 1 overly broad exception catch (`Exception` on line 267)

**Recommendations:**
- Break long lines or adjust line length limit for examples
- Remove unused variable or use it
- Consider making protected members public or using proper accessors
- Catch more specific exceptions

### 4. Code Quality Issues

**Commented-out Code:**
- `src/InkGen/component.py` lines 259-263: Commented-out validation code that was intentionally removed

**Inconsistent Return Types:**
- `Style.create_from_dict()` and similar methods in `style.py` have incorrect return type annotations (`-> None` instead of the actual class type)

**Missing Type Hints:**
- Some function parameters lack type hints (e.g., `_px_to_units` originally had no type hints - now fixed)
- Some properties lack return type hints

### 5. Potential Unused Imports
- `sys` import in `component.py` - used for dynamic class loading, so likely needed
- `sys` import in `document.py` - used for dynamic class loading, so likely needed
- `sys` import in `svg_generator.py` - used for dynamic class loading, so likely needed

### 6. Documentation Module Header
**File: `svg_generator.py`**
- Contains a "Problems" section in the module docstring (lines 4-8) that appears to be TODO items or legacy notes. Consider:
  - Moving to a TODO file
  - Removing if resolved
  - Updating if still relevant

## Recommendations

### High Priority
1. **Fix return type hints**: Replace all `-> object` with specific class types
2. **Fix incorrect return types**: Methods returning `None` that should return class instances
3. **Add missing docstrings**: Especially for public methods and properties

### Medium Priority
4. **Fix linting issues in examples**: Address line length, unused variables, and protected member access
5. **Clean up module docstrings**: Remove or update legacy "Problems" sections

### Low Priority
6. **Review commented-out code**: Decide if it should be removed or kept for reference
7. **Standardize docstring format**: Ensure all docstrings follow the same style (Google, NumPy, or Sphinx)

## Files Reviewed
- ✅ `src/InkGen/boundary.py`
- ✅ `src/InkGen/component.py`
- ✅ `src/InkGen/document.py`
- ✅ `src/InkGen/errors.py`
- ✅ `src/InkGen/style.py`
- ✅ `src/InkGen/svg_generator.py`
- ✅ `src/InkGen/svg_utils.py`
- ✅ `src/InkGen/table.py`
- ✅ `src/InkGen/text_fitter.py`
- ✅ `src/InkGen/text_outline.py`
- ✅ `src/InkGen/cad_component_groups.py`
- ✅ `src/InkGen/__init__.py`
- ⚠️ `examples/run_inkgen_primitives.py` (linting issues found)

## Statistics
- **Files reviewed**: 13 source files + 1 example file
- **Issues fixed**: 8
- **Issues remaining**: ~30+ (mostly type hints and docstrings)
- **Legacy code removed**: 1 function
- **Documentation added**: 6 docstrings
