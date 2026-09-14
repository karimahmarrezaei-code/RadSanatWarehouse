# -*- coding: utf-8 -*-
"""
Simple string replacements to make labels Persian
Run: python persian_labels.py
"""
import os, sys, py_compile

BASE = os.path.dirname(os.path.abspath(__file__))
PF = os.path.join(BASE, 'app', 'ui', 'proforma_window.py')

if not os.path.isfile(PF):
    print("ERROR: proforma_window.py not found!")
    sys.exit(1)

with open(PF, 'r', encoding='utf-8') as f:
    content = f.read()

# Simple safe replacements - only inside single-quoted strings
# These replacements only affect text INSIDE Python string literals
replacements = [
    # Window title
    ("'Proforma Invoice Manager'", "'\u0645\u062f\u06cc\u0631\u06cc\u062a \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631'"),
    ("'Create, view and print proforma invoices'", "'\u062b\u0628\u062a\u060c \u0645\u0634\u0627\u0647\u062f\u0647 \u0648 \u0686\u0627\u067e \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631\u0647\u0627'"),
    
    # Tab names
    ("'New Proforma'", "'\u062b\u0628\u062a \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631 \u062c\u062f\u06cc\u062f'"),
    ("'Proforma List'", "'\u0644\u06cc\u0633\u062a \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631\u0647\u0627'"),
    
    # Close button
    ("'Close'", "'\u0628\u0633\u062a\u0646'"),
    
    # Group boxes
    ("'Proforma Info'", "'\u0627\u0637\u0644\u0627\u0639\u0627\u062a \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631'"),
    ("'Proforma Items'", "'\u0631\u062f\u06cc\u0641\u0647\u0627\u06cc \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631'"),
    
    # Form labels
    ("'Proforma No:'", "'\u0634\u0645\u0627\u0631\u0647 \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631:'"),
    ("'Date:'", "'\u062a\u0627\u0631\u06cc\u062e:'"),
    ("'Customer:'", "'\u0645\u0634\u062a\u0631\u06cc:'"),
    ("'Validity (days):'", "'\u0627\u0639\u062a\u0628\u0627\u0631 (\u0631\u0648\u0632):'"),
    ("'Description:'", "'\u062a\u0648\u0636\u06cc\u062d\u0627\u062a:'"),
    ("'Validity days'", "'\u062a\u0639\u062f\u0627\u062f \u0631\u0648\u0632 \u0627\u0639\u062a\u0628\u0627\u0631'"),
    ("'Description...'", "'\u062a\u0648\u0636\u06cc\u062d\u0627\u062a \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631...'"),
    
    # Buttons
    ("'Save Proforma'", "'\u062b\u0628\u062a \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631'"),
    ("'Preview'", "'\u067e\u06cc\u0634\u0646\u0645\u0627\u06cc\u0634'"),
    ("'New Form'", "'\u0641\u0631\u0645 \u062c\u062f\u06cc\u062f'"),
    ("'Select Customer'", "'\u0627\u0646\u062a\u062e\u0627\u0628 \u0645\u0634\u062a\u0631\u06cc'"),
    
    # Filter
    ("'Filter'", "'\u0641\u06cc\u0644\u062a\u0631'"),
    ("'From:'", "'\u0627\u0632 \u062a\u0627\u0631\u06cc\u062e:'"),
    ("'To:'", "'\u062a\u0627 \u062a\u0627\u0631\u06cc\u062e:'"),
    ("'All Customers'", "'\u0647\u0645\u0647 \u0645\u0634\u062a\u0631\u06cc\u0627\u0646'"),
    ("'Refresh'", "'\u0628\u0631\u0648\u0632\u0631\u0633\u0627\u0646\u06cc'"),
    
    # Table headers
    ("'ID'", "'\u0634\u0646\u0627\u0633\u0647'"),
    ("'No'", "'\u0634\u0645\u0627\u0631\u0647'"),
    ("'Date'", "'\u062a\u0627\u0631\u06cc\u062e'"),
    ("'Customer'", "'\u0645\u0634\u062a\u0631\u06cc'"),
    ("'Items'", "'\u062a\u0639\u062f\u0627\u062f \u0631\u062f\u06cc\u0641'"),
    ("'Total'", "'\u062c\u0645\u0639 \u06a9\u0644'"),
    ("'Validity'", "'\u0627\u0639\u062a\u0628\u0627\u0631'"),
    ("'Status'", "'\u0648\u0636\u0639\u06cc\u062a'"),
    
    # Status labels
    ("'Draft'", "'\u067e\u06cc\u0634\u0646\u0648\u06cc\u0633'"),
    ("'Final'", "'\u0646\u0647\u0627\u06cc\u06cc'"),
    ("'Converted'", "'\u062a\u0628\u062f\u06cc\u0644 \u0634\u062f\u0647'"),
    ("'Cancelled'", "'\u0628\u0627\u0637\u0644 \u0634\u062f\u0647'"),
    
    # Buttons (list)
    ("'View Details'", "'\u0645\u0634\u0627\u0647\u062f\u0647 \u062c\u0632\u0626\u06cc\u0627\u062a'"),
    ("'Print'", "'\u0686\u0627\u067e'"),
    ("'Delete'", "'\u062d\u0630\u0641'"),
    
    # Rial and days
    ("' Rial'", "' \u0631\u06cc\u0627\u0644'"),
    ("' days'", "' \u0631\u0648\u0632'"),
    
    # Dialogs
    ("'Notice'", "'\u062a\u0648\u062c\u0647'"),
    ("'Error'", "'\u062e\u0637\u0627'"),
    ("'Success'", "'\u0645\u0648\u0641\u0642'"),
    ("'Confirm'", "'\u062a\u0623\u06cc\u06cc\u062f'"),
    
    # Messages
    ("'Select a proforma.'", "'\u0627\u0628\u062a\u062f\u0627 \u06cc\u06a9 \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f.'"),
    ("'Not found.'", "'\u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631 \u06cc\u0627\u0641\u062a \u0646\u0634\u062f.'"),
    ("'Already converted.'", "'\u0627\u06cc\u0646 \u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631 \u0642\u0628\u0644\u0627\u064b \u062a\u0628\u062f\u06cc\u0644 \u0634\u062f\u0647.'"),
    ("'No items.'", "'\u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631 \u0641\u0627\u0642\u062f \u0622\u06cc\u062a\u0645 \u0627\u0633\u062a.'"),
    ("'Select a customer.'", "'\u0644\u0637\u0641\u0627\u064b \u0645\u0634\u062a\u0631\u06cc \u0631\u0627 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f.'"),
    ("'Add at least one item.'", "'\u062d\u062f\u0627\u0642\u0644 \u06cc\u06a9 \u0631\u062f\u06cc\u0641 \u0627\u0636\u0627\u0641\u0647 \u06a9\u0646\u06cc\u062f.'"),
    ("'Select a pallet.'", "'\u0644\u0637\u0641\u0627\u064b \u067e\u0627\u0644\u062a \u0631\u0627 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f.'"),
    ("'Quantity must be greater than zero.'", "'\u062a\u0639\u062f\u0627\u062f \u0628\u0627\u06cc\u062f \u0628\u06cc\u0634\u062a\u0631 \u0627\u0632 \u0635\u0641\u0631 \u0628\u0627\u0634\u062f.'"),
    ("'List error:\\n'", "'\u062e\u0637\u0627 \u062f\u0631 \u0628\u0627\u0631\u06af\u0630\u0627\u0631\u06cc \u0644\u06cc\u0633\u062a:\\n'"),
    ("'View error:\\n'", "'\u062e\u0637\u0627 \u062f\u0631 \u0646\u0645\u0627\u06cc\u0634:\\n'"),
    ("'Save error:\\n'", "'\u062e\u0637\u0627 \u062f\u0631 \u062b\u0628\u062a:\\n'"),
    ("'Delete error:\\n'", "'\u062e\u0637\u0627 \u062f\u0631 \u062d\u0630\u0641:\\n'"),
    ("'Proforma deleted.'", "'\u067e\u06cc\u0634\u0641\u0627\u06a9\u062a\u0648\u0631 \u062d\u0630\u0641 \u0634\u062f.'"),
    ("'No driver found.'", "'\u0631\u0627\u0646\u0646\u062f\u0647\u0627\u06cc \u06cc\u0627\u0641\u062a \u0646\u0634\u062f.'"),
    ("'Could not create outbound_load:\\n'", "'\u062e\u0637\u0627 \u062f\u0631 \u0633\u0627\u062e\u062a \u0628\u0627\u0631\u0646\u0627\u0645\u0647:\\n'"),
    ("'Could not create warehouse_issue:\\n'", "'\u062e\u0637\u0627 \u062f\u0631 \u0633\u0627\u062e\u062a \u062d\u0648\u0627\u0644\u0647:\\n'"),
    ("'Convert error:\\n'", "'\u062e\u0637\u0627 \u062f\u0631 \u062a\u0628\u062f\u06cc\u0644:\\n'"),
    ("'Add a person first.'", "'\u06cc\u06a9 \u0634\u062e\u0635 \u0627\u0636\u0627\u0641\u0647 \u06a9\u0646\u06cc\u062f.'"),
    ("' converted.\\nIssue No: '", "' \u062a\u0628\u062f\u06cc\u0644 \u0634\u062f.\\n\u0634\u0645\u0627\u0631\u0647 \u062d\u0648\u0627\u0644\u0647: '"),
    ("'Confirm price?'", "'\u062a\u0623\u06cc\u06cc\u062f \u0642\u06cc\u0645\u062a\u061f'"),
    ("'Price is lower than average. Continue?'", "'\u0642\u06cc\u0645\u062a \u06a9\u0645\u062a\u0631 \u0627\u0632 \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0627\u0633\u062a. \u0627\u062f\u0627\u0645\u0647 \u0645\u06cc\u062f\u0647\u06cc\u062f\u061f'"),
]

changes = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        changes += 1

print(f"Replaced {changes} labels with Persian")

# Also fix main_window.py references if any
MW = os.path.join(BASE, 'app', 'ui', 'main_window.py')
if os.path.isfile(MW):
    with open(MW, 'r', encoding='utf-8') as f:
        mw = f.read()
    if 'ProformaInvoiceWindow' in mw:
        # The window title is set inside the window, no changes needed in main_window
        pass

with open(PF, 'w', encoding='utf-8') as f:
    f.write(content)

try:
    py_compile.compile(PF, doraise=True)
    print("[OK] syntax OK!")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

print("\nDONE! Run: python -m app.main")
