"""Compatibility wrapper around the bundled PyMySQL implementation.

The addon expects the older mysql.connector import surface. We expose the modern
PyMySQL API under that name so all runtime imports keep working without any
external dependency.
"""

from lib.mysql import pymysql as _pymysql

# Exception hierarchy
Error = _pymysql.Error
Warning = _pymysql.Warning
InterfaceError = _pymysql.InterfaceError
DatabaseError = _pymysql.DatabaseError
NotSupportedError = _pymysql.NotSupportedError
DataError = _pymysql.DataError
IntegrityError = _pymysql.IntegrityError
ProgrammingError = _pymysql.ProgrammingError
OperationalError = _pymysql.OperationalError
InternalError = _pymysql.InternalError
MySQLError = _pymysql.MySQLError

# Main API
connect = _pymysql.connect
Connect = connect
Connection = _pymysql.Connection

# DB-API compatibility names expected by existing code
Date = _pymysql.Date
Time = _pymysql.Time
Timestamp = _pymysql.Timestamp
DateFromTicks = _pymysql.DateFromTicks
TimeFromTicks = _pymysql.TimeFromTicks
TimestampFromTicks = _pymysql.TimestampFromTicks
BINARY = _pymysql.BINARY
NUMBER = _pymysql.NUMBER
STRING = _pymysql.STRING
DATETIME = _pymysql.DATETIME
ROWID = _pymysql.ROWID
apilevel = _pymysql.apilevel
threadsafety = _pymysql.threadsafety
paramstyle = _pymysql.paramstyle

# Minimal placeholders used by legacy connector code; the addon only needs the
# connection object and errors.
FieldType = getattr(_pymysql, 'FIELD_TYPE', object)
FieldFlag = getattr(_pymysql, 'FIELD_TYPE', object)
CharacterSet = getattr(_pymysql.constants, 'CharacterSet', object)
ClientFlag = getattr(_pymysql.constants, 'CLIENT', object)
RefreshOption = object

__version__ = getattr(_pymysql, '__version__', '2.2.8')
__version_info__ = getattr(_pymysql, 'version_info', (2, 2, 8, 'final', 1))

__all__ = [
    'connect', 'Connect', 'Connection',
    'Error', 'Warning', 'InterfaceError', 'DatabaseError',
    'NotSupportedError', 'DataError', 'IntegrityError',
    'ProgrammingError', 'OperationalError', 'InternalError',
    'MySQLError',
    'Date', 'Time', 'Timestamp', 'DateFromTicks', 'TimeFromTicks',
    'TimestampFromTicks', 'BINARY', 'NUMBER', 'STRING',
    'DATETIME', 'ROWID', 'apilevel', 'threadsafety', 'paramstyle',
    'FieldType', 'FieldFlag', 'CharacterSet', 'ClientFlag', 'RefreshOption',
    '__version__', '__version_info__',
]
