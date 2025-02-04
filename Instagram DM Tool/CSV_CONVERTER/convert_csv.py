import pandas as pd
from io import StringIO

data = '''username,name,message
''' + open('input.txt').read()

# Convert to DataFrame
df = pd.read_csv(StringIO(data))

# Save to CSV
df.to_csv('coaches.csv', index=False, encoding='utf-8', quoting=1)

print("CSV file created successfully")