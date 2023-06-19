import pymysql

connection = pymysql.connect(
    host='localhost',
    user='root',
    password='365Pass',
    db='taxi_prediction',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)