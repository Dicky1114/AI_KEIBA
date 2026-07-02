# メモ
### Django

```bash
source Projects/Django/bin/activate
cd Projects/Django/src/django_work/
python manage.py runserver
redis-server
celery -A horse worker --loglevel=info


```

```bash
brew install redis

```


```bash
pip install psycopg2
pip install sqlparse
pip install django
pip install celery
pip install bootstrap4
pip install django.import_export
pip install bs4
pip install pandas
pip install selenium
ip install -U "celery[redis]"
pip install -U redis
pip install lxml
```

```bash
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```
### SQL Query

```bash
psql d_db
¥dt
¥dv
```

#### Create View


- A view that displays the data where the results agree with the base data
```sql
CREATE VIEW v_compare_base_result AS
SELECT 
    r.race_id, 
    r.horse_number, 
    r.race_date
FROM 
    result_info r
INNER JOIN 
    base_info b
ON 
    r.race_id = b.race_id 
    AND r.horse_number = b.horse_number 
    AND r.race_date = b.race_date

UNION

SELECT 
    u.race_id, 
    NULL AS horse_number,
    u.race_date
FROM 
    url_mst u
WHERE 
    u.race_id like '%dummy%';

```

```sql
CREATE VIEW v_create_race_ids AS
WITH generated_race_ids AS (
    SELECT 
        lef || LPAD(generated_num::text, 2, '0') AS race_id
    FROM (
        SELECT DISTINCT lef
        FROM (
            SELECT 
                LEFT(race_id, 10) AS lef
            FROM 
                v_compare_base_result
            GROUP BY 
                race_id
        ) subquery
    ) distinct_lef,
    generate_series(1, 12) AS generated_num
)
SELECT 
    generated_race_ids.race_id,
    CONCAT('https://race.netkeiba.com/race/shutuba.html?race_id=', generated_race_ids.race_id) AS url
FROM 
    generated_race_ids
LEFT JOIN 
    v_compare_base_result
ON 
    generated_race_ids.race_id = v_compare_base_result.race_id
WHERE 
    v_compare_base_result.race_id IS NULL
AND
    generated_race_ids.race_id NOT LIKE '%dummy%'
ORDER BY 
    generated_race_ids.race_id ASC;
```

```sql
CREATE VIEW v_weekend AS
WITH calendar AS (
    SELECT 
        generate_series(
            '2000-01-01'::date, 
            CURRENT_DATE, 
            '1 day'
        )::date AS race_date
)
SELECT 
    row_number() OVER () AS id,
    calendar.race_date,
    url_mst.race_date as race_date_null,
    url_mst.race_id
FROM 
    calendar
LEFT JOIN 
    url_mst 
ON 
    calendar.race_date = url_mst.race_date::date
WHERE 
    EXTRACT(DOW FROM calendar.race_date) IN (0, 6)
    AND url_mst.race_date IS NULL
ORDER BY 
    calendar.race_date;
```

```sql
CREATE VIEW v_public_holiday AS
WITH calendar AS (
    SELECT 
        generate_series(
            '2000-01-01'::date, 
            CURRENT_DATE, 
            '1 day'
        )::date AS race_date
)
SELECT 
    url_mst.race_id,
    url_mst.race_date,
    url_mst.url
FROM 
    calendar
INNER JOIN 
    url_mst 
ON 
    calendar.race_date = url_mst.race_date::date
WHERE 
    EXTRACT(DOW FROM calendar.race_date) NOT IN (0, 6)
ORDER BY 
    calendar.race_date;
```

```sql
CREATE VIEW v_compare_horse_mst_tran AS (
    SELECT 
        horse_id, 
        horse_name,
        CONCAT('https://db.netkeiba.com/horse/', horse_id) as horse_url
    FROM t_horse_info t1
    WHERE NOT EXISTS (
        SELECT 1 
        FROM m_horse m1
        WHERE m1.horse_id = t1.horse_id
    )
);
```

```sql

CREATE OR REPLACE VIEW v_compare_base_horse AS 
WITH CTE_A AS (
    SELECT
        MAX(RACE_DATE) AS MAX_RACE_DATE,
        HORSE_URL,
        HORSE_NAME

    FROM
        T_BASE_INFO
    GROUP BY
        HORSE_URL, HORSE_NAME
),
CTE_B AS (
    SELECT
        T1.MAX_RACE_DATE,
        T1.HORSE_URL,
        T1.HORSE_NAME,
        T2.MAX_HORSE_RACE_DATE
    FROM
        CTE_A T1
    LEFT JOIN (
        SELECT
            T2.HORSE_ID,
            MAX(T2.RACE_DATE) AS MAX_HORSE_RACE_DATE
        FROM
            T_HORSE_INFO T2
        GROUP BY
            T2.HORSE_ID
    ) T2 ON RIGHT(T1.HORSE_URL, 10) = T2.HORSE_ID
    WHERE 
        T1.MAX_RACE_DATE::DATE > T2.MAX_HORSE_RACE_DATE::DATE
        AND T1.MAX_RACE_DATE IS NOT NULL
)
SELECT         
	MAX_RACE_DATE AS RACE_DATE,
	HORSE_URL,
    HORSE_NAME,
	MAX_HORSE_RACE_DATE
FROM CTE_B
WHERE MAX_RACE_DATE::DATE > MAX_HORSE_RACE_DATE::DATE;


```

```sql

CREATE OR REPLACE VIEW v_compare_base_jockey AS 
WITH CTE_A AS (
    SELECT
        MAX(RACE_DATE) AS MAX_RACE_DATE,
        JOCKEY_URL,
        JOCKEY_NAME
    FROM
        T_BASE_INFO
    GROUP BY
        JOCKEY_URL, JOCKEY_NAME
),
CTE_B AS (
    SELECT
        T1.MAX_RACE_DATE,
        T1.JOCKEY_URL,
        T1.JOCKEY_NAME,
        T2.MAX_JOCKEY_RACE_DATE
    FROM
        CTE_A T1
    LEFT JOIN (
        SELECT
            T2.JOCKEY_ID,
            MAX(T2.RACE_DATE) AS MAX_JOCKEY_RACE_DATE
        FROM
            T_JOCKEY_INFO T2
        GROUP BY
            T2.JOCKEY_ID
    ) T2 ON LEFT(RIGHT(T1.JOCKEY_URL, 12), 5) = T2.JOCKEY_ID
    WHERE 
        T1.MAX_RACE_DATE::DATE > T2.MAX_JOCKEY_RACE_DATE::DATE
        AND T1.MAX_RACE_DATE IS NOT NULL
)
SELECT         
	MAX_RACE_DATE AS RACE_DATE,
	JOCKEY_URL,
    JOCKEY_NAME,
    MAX_JOCKEY_RACE_DATE
FROM CTE_B
WHERE MAX_RACE_DATE::DATE > MAX_JOCKEY_RACE_DATE::DATE;



```

### ターミナルコマンド

### 非同期処理
```bash
brew services start redis
redis-server
celery -A horse worker --loglevel=info

```
