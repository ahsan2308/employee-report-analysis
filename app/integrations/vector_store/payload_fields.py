"""
Payload fields of a report chunk in the vector store.

The collection's payload indexes, the payload written for each chunk and the
search filters must all use the same names, so they all use these.
"""

EMPLOYEE_ID = "employee_id"    # indexed: keyword, tenant-aware
REPORT_ID = "report_id"        # indexed: keyword
CHUNK_INDEX = "chunk_index"
REPORT_DATE = "report_date"    # the date as given, for display
REPORT_DATE_TS = "report_date_ts"  # indexed: float timestamp, for date filters
TEXT = "text"                  # indexed: full text
