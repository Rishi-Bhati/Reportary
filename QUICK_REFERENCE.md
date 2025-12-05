# Quick Reference: Form Submit Fix

## The Problems
1. **Submit button didn't work** → "NOT NULL constraint failed: reports_report.project_id"
2. **Security risk** → Hidden project field was exposed in HTML, could be tampered with

## The Root Causes

| Problem | Root Cause |
|---------|-----------|
| Submit failed | Project was NULL when saving → form had no project field → database rejected NULL |
| Hidden field exposed | Using `HiddenInput()` widget → still rendered as HTML → visible in DevTools |

## The Solution

### ✅ Remove field entirely instead of hiding it
```python
# WRONG ❌
self.fields['project'].widget = forms.HiddenInput()

# RIGHT ✅
del self.fields['project']
```

### ✅ Set project BEFORE saving, not after
```python
# WRONG ❌
report.save()
if project:
    report.project = project

# RIGHT ✅
if self.project:
    instance.project = self.project
instance.save()
```

### ✅ Store trusted data in form instance
```python
self.project = project  # Store URL param
# Later in save():
instance.project = self.project  # Use stored value
```

### ✅ Validate project requirement
```python
# In clean() method
if self.project is None and 'project' not in cleaned_data:
    raise forms.ValidationError("Project is required.")
```

## How It Works Now

| URL | Field Status | Data Flow |
|-----|--------------|-----------|
| `/reports/new/` | Project field SHOWN | User selects → form submission → save() |
| `/projects/3/reports/new/` | Project field HIDDEN | URL param → form init → save() |

## Why It's Secure

1. **No hidden fields in HTML** → Nothing to inspect/tamper
2. **Backend enforces project** → View + Form + DB all check
3. **URL parameter is source of truth** → Not form submission
4. **Multiple validation layers** → If one fails, others catch it

## Files Modified

1. **forms.py** - Form logic (remove field, validate, save)
2. **views.py** - View logic (pass project, handle both workflows)
3. **template** - Render based on project availability
4. **SOLUTION_EXPLANATION.md** - Detailed documentation (NEW)

## Testing

### ✅ Should work:
- Click "+New Report" from dashboard → Select project → Submit
- Click "Report Issue" from project page → Submit (project pre-selected)

### ❌ Should fail gracefully:
- Submit without selecting project from /reports/new/ → Validation error
- Try to modify hidden fields → No fields to modify
- Try to report to different project → URL validation fails
