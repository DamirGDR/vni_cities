import pandas as pd
import pymysql
from sqlalchemy import create_engine
import os
import psycopg2 as pg

#Секреты MySQL

# Из окружения
user_mysql = os.environ["user_mysql"]
password_mysql = os.environ["password_mysql"]
host_mysql = os.environ["host_mysql"]
port_mysql = os.environ["port_mysql"]
db_mysql = os.environ["db_mysql"]


# Секреты Postgres

# Из окружения
user_postgres = os.environ["user_postgres"]
password_postgres = os.environ["password_postgres"]
host_postgres = os.environ["host_postgres"]
port_postgres = os.environ["port_postgres"]
db_postgres = os.environ["db_postgres"]

def main():
    # Выгрузка за сегодня из MySQL
    select = '''
    WITH three_left_cols AS 
    (    
        SELECT 
        three_left_cols.start_time,
        three_left_cols.city_id,
        three_left_cols.poezdok,
        three_left_cols.obzchaya_stoimost,
        SUM(three_left_cols.obzchaya_stoimost) OVER(PARTITION BY three_left_cols.city_id ORDER BY three_left_cols.start_time) AS 'obzchaya_stoimost_ni',
        three_left_cols.oplacheno_bonusami,
        SUM(three_left_cols.oplacheno_bonusami) OVER(PARTITION BY three_left_cols.city_id ORDER BY three_left_cols.start_time) AS 'oplacheno_bonusami_ni',
        three_left_cols.obschee_vremya_min
    FROM 
        (SELECT 
            DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d') AS  'start_time',
            t_bike.city_id,
            COUNT(t_bike_use.ride_amount) AS 'poezdok',
            SUM(t_bike_use.ride_amount) AS 'obzchaya_stoimost',
            SUM(t_bike_use.discount) AS 'oplacheno_bonusami',
            SUM(t_bike_use.duration) / 60 AS 'obschee_vremya_min'
        FROM shamri.t_bike_use
        LEFT JOIN t_bike ON t_bike_use.bid = t_bike.id
        WHERE t_bike_use.ride_status!=5
        GROUP BY DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d'), t_bike.city_id
        ORDER BY DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d') DESC) AS three_left_cols
    ),
    sum_uspeh_abon AS (
        SELECT 
            distr_poezdki_po_gorodam.start_time,
            distr_poezdki_po_gorodam.city_id,
            distr_poezdki_po_gorodam.coef_goroda,
            sum_uspeh_abon.vyruchka_s_abonementov AS 'vyruchka_s_abonementov_po_vsem_gorodam',
            sum_uspeh_abon.vyruchka_s_abonementov * distr_poezdki_po_gorodam.coef_goroda AS 'vyruchka_s_abonementov',
            SUM(sum_uspeh_abon.vyruchka_s_abonementov * distr_poezdki_po_gorodam.coef_goroda) OVER (PARTITION BY distr_poezdki_po_gorodam.city_id ORDER BY distr_poezdki_po_gorodam.start_time) AS 'vyruchka_s_abonementov_ni'
        FROM (
            -- высчитываю пропорции по поездкам
            SELECT 
                distr_poezdki_po_gorodam.start_time,
                distr_poezdki_po_gorodam.city_id,
                distr_poezdki_po_gorodam.poezdok / SUM(distr_poezdki_po_gorodam.poezdok) OVER (PARTITION BY distr_poezdki_po_gorodam.start_time) AS 'coef_goroda'
            FROM 
                (SELECT 
                    DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d') AS  'start_time',
                    t_bike.city_id,
                    COUNT(t_bike_use.ride_amount) AS 'poezdok'
                FROM shamri.t_bike_use
                LEFT JOIN t_bike ON t_bike_use.bid = t_bike.id
                WHERE t_bike_use.ride_status!=5 
                GROUP BY DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d'), t_bike.city_id
                ORDER BY DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d') DESC) 
                AS distr_poezdki_po_gorodam
            ORDER BY distr_poezdki_po_gorodam.start_time DESC
        ) AS distr_poezdki_po_gorodam
        LEFT JOIN (
            SELECT 
                DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                sum(t_trade.amount) AS vyruchka_s_abonementov
            FROM shamri.t_trade
            WHERE t_trade.`type` = 6 
                AND t_trade.status = 1 
            GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d')
            ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC
        ) AS sum_uspeh_abon
        ON distr_poezdki_po_gorodam.start_time = sum_uspeh_abon.start_time
    ),
    sum_mnogor_abon AS (
        SELECT 
            distr_poezdki_po_gorodam.start_time,
            distr_poezdki_po_gorodam.city_id,
            distr_poezdki_po_gorodam.coef_goroda,
            sum_mnogor_abon.sum_mnogor_abon AS 'sum_mnogor_abon_vsego',
            sum_mnogor_abon.sum_mnogor_abon * distr_poezdki_po_gorodam.coef_goroda AS 'sum_mnogor_abon',
            SUM(sum_mnogor_abon.sum_mnogor_abon * distr_poezdki_po_gorodam.coef_goroda) OVER (PARTITION BY distr_poezdki_po_gorodam.city_id ORDER BY distr_poezdki_po_gorodam.start_time) AS 'sum_mnogor_abon_ni'
        FROM (
    -- высчитываю пропорции по поездкам
        SELECT 
            distr_poezdki_po_gorodam.start_time,
            distr_poezdki_po_gorodam.city_id,
            distr_poezdki_po_gorodam.poezdok / SUM(distr_poezdki_po_gorodam.poezdok) OVER (PARTITION BY distr_poezdki_po_gorodam.start_time) AS 'coef_goroda'
        FROM 
            (SELECT 
                DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d') AS  'start_time',
                t_bike.city_id,
                COUNT(t_bike_use.ride_amount) AS 'poezdok'
            FROM shamri.t_bike_use
            LEFT JOIN t_bike ON t_bike_use.bid = t_bike.id
            WHERE t_bike_use.ride_status!=5 
            GROUP BY DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d'), t_bike.city_id
            ORDER BY DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d') DESC) 
            AS distr_poezdki_po_gorodam
        ORDER BY distr_poezdki_po_gorodam.start_time DESC
        ) AS distr_poezdki_po_gorodam
        LEFT JOIN (
            SELECT 
                DATE_FORMAT(t_subscription_mapping.start_time, '%%Y-%%m-%%d') AS start_time,
                sum(t_subscription.price) AS sum_mnogor_abon
            FROM t_subscription_mapping
            LEFT JOIN t_subscription ON t_subscription_mapping.subscription_id = t_subscription.id
            GROUP BY DATE_FORMAT(t_subscription_mapping.start_time, '%%Y-%%m-%%d')
            ORDER BY DATE_FORMAT(t_subscription_mapping.start_time, '%%Y-%%m-%%d') DESC
            ) AS sum_mnogor_abon
        ON distr_poezdki_po_gorodam.start_time = sum_mnogor_abon.start_time
        ORDER BY distr_poezdki_po_gorodam.start_time DESC
    ),
    kvt AS (
        SELECT 
            DATE_FORMAT(FROM_UNIXTIME(t_bike.heart_time), '%%Y-%%m-%%d') AS start_time,
            t_bike.city_id,
            COUNT(t_bike.id) AS kvt
        FROM t_bike
        WHERE TIMESTAMPDIFF(SECOND, now(), DATE_FORMAT(FROM_UNIXTIME(t_bike.g_time), '%%Y-%%m-%%d %%H:%%m:%%s')) < 900 
            AND t_bike.error_status IN (0, 7) 
        GROUP BY DATE_FORMAT(FROM_UNIXTIME(t_bike.heart_time), '%%Y-%%m-%%d'), t_bike.city_id
        HAVING start_time = DATE_FORMAT(NOW(), '%%Y-%%m-%%d') AND COUNT(t_bike.id) > 10
        ORDER BY t_bike.city_id DESC
    ),
    vyruchka_uspeh_payTabs AS 
    (
        SELECT
            vyruchka_uspeh_payTabs.start_time,
            vyruchka_uspeh_payTabs.city_id,
            vyruchka_uspeh_payTabs.vyruchka_v_statuse_1_payTabs,
            SUM(vyruchka_uspeh_payTabs.vyruchka_v_statuse_1_payTabs) OVER (PARTITION BY vyruchka_uspeh_payTabs.city_id ORDER BY vyruchka_uspeh_payTabs.start_time) AS 'vyruchka_v_statuse_1_payTabs_ni'
        FROM
            (SELECT 
                DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                t_trade.city_id,
                SUM(t_trade.account_pay_amount) AS 'vyruchka_v_statuse_1_payTabs'
            FROM t_trade
            WHERE t_trade.status=1 
                AND t_trade.way=26 
                AND t_trade.`type` IN (1,2,5,6,7) 
            GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d'), t_trade.city_id
            ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC, t_trade.city_id DESC) AS vyruchka_uspeh_payTabs
    ),
    vyruchka_uspeh_payTabs_ni AS 
    (
         SELECT
             vyruchka_uspeh_payTabs.city_id,
             vyruchka_uspeh_payTabs.start_time, 
            vyruchka_uspeh_payTabs.vyruchka_v_statuse_1_payTabs_ni AS 'vyruchka_v_statuse_1_payTabs_ni'
         FROM 
            (SELECT
                vyruchka_uspeh_payTabs.start_time,
                vyruchka_uspeh_payTabs.city_id,
                vyruchka_uspeh_payTabs.vyruchka_v_statuse_1_payTabs,
                SUM(vyruchka_uspeh_payTabs.vyruchka_v_statuse_1_payTabs) OVER (PARTITION BY vyruchka_uspeh_payTabs.city_id ORDER BY vyruchka_uspeh_payTabs.start_time) AS 'vyruchka_v_statuse_1_payTabs_ni'
            FROM
                (SELECT 
                    DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                    t_trade.city_id,
                    SUM(t_trade.account_pay_amount) AS 'vyruchka_v_statuse_1_payTabs'
                FROM t_trade
                WHERE t_trade.status=1 
                    AND t_trade.way=26 
                    AND t_trade.`type` IN (1,2,5,6,7) 
                GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d'), t_trade.city_id
                ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC, t_trade.city_id DESC) AS vyruchka_uspeh_payTabs)
            AS vyruchka_uspeh_payTabs
    ),
    vosvraty_payTabs AS ( 
        SELECT
            trade.start_time,
            trade.city_id,
            trade.vozvraty_payTabs,
            SUM(trade.vozvraty_payTabs) OVER (PARTITION BY trade.city_id ORDER BY trade.start_time) AS 'vozvraty_payTabs_ni'
        FROM
            (SELECT
                DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                t_trade.city_id,
                IFNULL(SUM(t_trade.account_pay_amount), 0) AS 'vozvraty_payTabs'
            FROM t_trade
            WHERE t_trade.status=4 
                 AND t_trade.way=26 
            GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d'), t_trade.city_id
            ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC) AS trade
     ),
     vozvraty_payTabs_ni AS (
         SELECT
             vozvraty_payTabs.city_id,
             vozvraty_payTabs.start_time,
             vozvraty_payTabs.vozvraty_payTabs_ni
         FROM 
            (SELECT
                trade.start_time,
                trade.city_id,
                trade.vozvraty_payTabs,
                SUM(trade.vozvraty_payTabs) OVER (PARTITION BY trade.city_id ORDER BY trade.start_time) AS 'vozvraty_payTabs_ni'
            FROM
                (SELECT
                    DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                    t_trade.city_id,
                    IFNULL(SUM(t_trade.account_pay_amount), 0) AS 'vozvraty_payTabs'
                FROM t_trade
                WHERE t_trade.status=4 
                     AND t_trade.way=26 
                GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d'), t_trade.city_id
                ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC) AS trade) AS vozvraty_payTabs
     ),
    uspeh_Stripe AS (
        SELECT
            trade.start_time,
            trade.city_id,
            trade.uspeh_Stripe,
            SUM(IFNULL(trade.uspeh_Stripe, 0)) OVER (PARTITION BY trade.city_id ORDER BY trade.start_time) AS 'uspeh_Stripe_ni'
        FROM 
            (SELECT 
                DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                t_trade.city_id,
                SUM(t_trade.account_pay_amount) AS 'uspeh_Stripe'
            FROM t_trade
            WHERE t_trade.status=1 
                 AND t_trade.way=6 
            GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d'), t_trade.city_id
            ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC) AS trade
     ),
     uspeh_Stripe_ni AS(
         SELECT 
             uspeh_Stripe.city_id,
             uspeh_Stripe.start_time,
            uspeh_Stripe.uspeh_Stripe,
            uspeh_Stripe.uspeh_Stripe_ni
         FROM 
            (SELECT
                trade.start_time,
                trade.city_id,
                trade.uspeh_Stripe,
                SUM(IFNULL(trade.uspeh_Stripe, 0)) OVER (PARTITION BY trade.city_id ORDER BY trade.start_time) AS 'uspeh_Stripe_ni'
            FROM 
                (SELECT 
                    DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                    t_trade.city_id,
                    SUM(t_trade.account_pay_amount) AS 'uspeh_Stripe'
                FROM t_trade
                WHERE t_trade.status=1 
                     AND t_trade.way=6 
                GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d'), t_trade.city_id
                ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC) AS trade) 
            AS uspeh_Stripe
     ),
     vozvraty_Stripe AS (
        SELECT
            trade.start_time,
            trade.city_id,
            trade.vozvraty_Stripe,
            SUM(IFNULL(trade.vozvraty_Stripe, 0)) OVER (PARTITION BY trade.city_id ORDER BY trade.start_time) AS 'vozvraty_Stripe_ni'
        FROM
            (SELECT 
                DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                t_trade.city_id,
                SUM(t_trade.account_pay_amount) AS 'vozvraty_Stripe'
             FROM t_trade
             WHERE t_trade.status=4 
                 AND t_trade.way=6 
             GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d'), t_trade.city_id
             ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC) AS trade
     ),
     vozvraty_Stripe_ni AS (
         SELECT
             vozvraty_Stripe.city_id,
             vozvraty_Stripe.start_time,
             vozvraty_Stripe.vozvraty_Stripe_ni
         FROM 
            (SELECT
                trade.start_time,
                trade.city_id,
                trade.vozvraty_Stripe,
                SUM(IFNULL(trade.vozvraty_Stripe, 0)) OVER (PARTITION BY trade.city_id ORDER BY trade.start_time) AS 'vozvraty_Stripe_ni'
            FROM
                (SELECT 
                    DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') AS start_time,
                    t_trade.city_id,
                    SUM(t_trade.account_pay_amount) AS 'vozvraty_Stripe'
                 FROM t_trade
                 WHERE t_trade.status=4 
                     AND t_trade.way=6 
                 GROUP BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d'), t_trade.city_id
                 ORDER BY DATE_FORMAT(t_trade.`date`, '%%Y-%%m-%%d') DESC) AS trade)
            AS vozvraty_Stripe
     ),
    user_v_den_register AS (
        SELECT
            user_register.start_time,
            user_register.city_id,
            user_register.user_v_den_register,
            SUM(user_register.user_v_den_register) OVER (PARTITION BY user_register.city_id ORDER BY user_register.start_time) AS 'user_v_den_register_ni'
        FROM 
            (SELECT 
                DATE_FORMAT(t_user.register_date, '%%Y-%%m-%%d') AS start_time,
                t_user.city_id,
                COUNT(t_user.id) AS 'user_v_den_register'
            FROM t_user
            GROUP BY DATE_FORMAT(t_user.register_date, '%%Y-%%m-%%d'), t_user.city_id
            ORDER BY DATE_FORMAT(t_user.register_date, '%%Y-%%m-%%d') DESC) AS user_register
    ),
    kolichestvo_novyh_s_1_poezdkoy AS ( 
    SELECT
        register_date_as_start_date.start_date,
        register_date_as_start_date.city_id,
        COUNT(DISTINCT register_date_as_start_date.uid) AS 'kolichestvo_novyh_s_1_poezdkoy',
        COUNT(register_date_as_start_date.ride_amount) AS 'kolichestvo_poezdok_vsego'
    FROM
        (SELECT 
            DATE(DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d')) AS start_date, 
            t_bike_use.uid,
            t_bike_use.ride_amount,
            register_users.city_id,
            register_users.register_date,
            register_users.id AS register_user_id
        FROM t_bike_use
        LEFT JOIN (
            SELECT 
                DATE(DATE_FORMAT(t_user.register_date, '%%Y-%%m-%%d')) AS register_date, 
                t_user.id,
                t_user.city_id
            FROM t_user
                            ) AS register_users
        ON t_bike_use.uid=register_users.id
        WHERE t_bike_use.ride_status!=5 
            AND DATE(DATE_FORMAT(FROM_UNIXTIME(t_bike_use.start_time), '%%Y-%%m-%%d')) = DATE(DATE_FORMAT(register_users.register_date, '%%Y-%%m-%%d'))
        ) AS register_date_as_start_date
    GROUP BY register_date_as_start_date.start_date, register_date_as_start_date.city_id
    ORDER BY register_date_as_start_date.start_date DESC
    ),
    dolgi AS (
        SELECT 
            dolgi.create_debit_date,
            dolgi.city_id,
            dolgi.dolgi,
            SUM(dolgi.dolgi) OVER (PARTITION BY dolgi.city_id ORDER BY dolgi.create_debit_date) AS 'dolgi_ni'
        FROM 
            (SELECT 
                DATE_FORMAT(t_payment_details.created, '%%Y-%%m-%%d') AS 'create_debit_date', 
                dolgovye_poezdki.city_id,
                SUM(t_payment_details.debit_cash) AS 'dolgi'
            FROM t_payment_details
            RIGHT JOIN (
                    SELECT 
                        t_bike_use.id,
                        t_bike_use.uid,
                        t_bike_use.bid,
                        t_bike.city_id
                    FROM t_bike_use
                    LEFT JOIN t_bike ON t_bike_use.bid = t_bike.id
                    WHERE t_bike_use.ride_status = 2 
                        ) AS dolgovye_poezdki
            ON t_payment_details.user_id = dolgovye_poezdki.uid AND t_payment_details.ride_id = dolgovye_poezdki.id
            GROUP BY DATE_FORMAT(t_payment_details.created, '%%Y-%%m-%%d'), dolgovye_poezdki.city_id
            ORDER BY DATE_FORMAT(t_payment_details.created, '%%Y-%%m-%%d') DESC) AS dolgi
    ),
    t_city_with_noname AS (
        SELECT
            calendar.gen_date AS 'start_day',
            t_city_with_noname.id,
            t_city_with_noname.name
        FROM (
        select * from 
            (select adddate('1970-01-01',t4*10000 + t3*1000 + t2*100 + t1*10 + t0) gen_date from
             (select 0 t0 union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t0,
             (select 0 t1 union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t1,
             (select 0 t2 union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t2,
             (select 0 t3 union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t3,
             (select 0 t4 union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t4) v
            where gen_date between '2024-01-01' and DATE_FORMAT(NOW(), '%%Y-%%m-%%d')
        ) AS calendar
        CROSS JOIN (
            SELECT 
                t_city.*
            FROM t_city
            UNION
            SELECT 
                0 AS 'id', 
                'Unknown' AS 'name', 
                '' AS 'note', 
                NULL AS 'code', 
                '' AS 'area_detail', 
                0 AS 'area_lat', 
                0 AS 'area_lng', 
                NULL AS 'currency', 
                '00:00' AS 'start_time', 
                '00:24' AS 'end_time', 
                NULL AS 'invite_code', 
                '{"max_speed_limit":0}' AS 'extend_info', 
                1 AS 'industry_id'
        ) AS t_city_with_noname
    )
    SELECT 
        DATE_FORMAT(NOW(), '%%Y-%%m-%%d %%H:%%m:%%s') as 'timestamp',
        t_city_with_noname.start_day AS 'day_',
        t_city_with_noname.id AS 'city_id',
        t_city_with_noname.name AS 'city_name',
        IFNULL(three_left_cols.poezdok, 0)  AS 'rides',
        IFNULL(three_left_cols.poezdok, 0) / IFNULL(kvt.kvt, 0) AS 'avg_rides_per_bike',
        (IFNULL(three_left_cols.obzchaya_stoimost, 0) - IFNULL(sum_mnogor_abon.sum_mnogor_abon, 0) - IFNULL(three_left_cols.oplacheno_bonusami, 0) + IFNULL(sum_uspeh_abon.vyruchka_s_abonementov, 0)) / IFNULL(kvt.kvt, 0) AS 'revenue_per_sim',
        (IFNULL(three_left_cols.obzchaya_stoimost, 0) - IFNULL(sum_mnogor_abon.sum_mnogor_abon, 0) - IFNULL(three_left_cols.oplacheno_bonusami, 0) + IFNULL(sum_uspeh_abon.vyruchka_s_abonementov, 0)) / IFNULL(three_left_cols.poezdok, 0) AS 'avg_ride_price',
        IFNULL(three_left_cols.oplacheno_bonusami, 0) AS 'bonus_revenue',
        IFNULL(three_left_cols.obzchaya_stoimost, 0) - IFNULL(dolgi.dolgi, 0) - (IFNULL(sum_uspeh_abon.vyruchka_s_abonementov, 0) -  IFNULL(sum_mnogor_abon.sum_mnogor_abon, 0)) AS 'revenue',
        IFNULL(three_left_cols.obzchaya_stoimost, 0) - IFNULL(dolgi.dolgi, 0) - (IFNULL(sum_uspeh_abon.vyruchka_s_abonementov, 0) -  IFNULL(sum_mnogor_abon.sum_mnogor_abon, 0)) - IFNULL(three_left_cols.oplacheno_bonusami, 0) AS 'revenue_without_bonus',
        IFNULL(sum_uspeh_abon.vyruchka_s_abonementov, 0) AS 'revenue_from_subscription',
        IFNULL(three_left_cols.obzchaya_stoimost, 0) - IFNULL(sum_mnogor_abon.sum_mnogor_abon, 0) - IFNULL(dolgi.dolgi, 0) - IFNULL(three_left_cols.oplacheno_bonusami, 0) + IFNULL(sum_uspeh_abon.vyruchka_s_abonementov, 0) AS 'revenue_without_bonus_plus_revenue_from_subscription',
        IFNULL(three_left_cols.obzchaya_stoimost_ni, 0) - IFNULL(dolgi.dolgi_ni, 0) - (IFNULL(sum_uspeh_abon.vyruchka_s_abonementov_ni, 0) -  IFNULL(sum_mnogor_abon.sum_mnogor_abon_ni, 0)) AS 'vni',
        IFNULL(three_left_cols.obzchaya_stoimost_ni, 0) - IFNULL(dolgi.dolgi_ni, 0) - (IFNULL(sum_uspeh_abon.vyruchka_s_abonementov_ni, 0) -  IFNULL(sum_mnogor_abon.sum_mnogor_abon_ni, 0)) - IFNULL(three_left_cols.oplacheno_bonusami_ni, 0) + IFNULL(sum_uspeh_abon.vyruchka_s_abonementov_ni, 0) AS 'vni_without_bonus',
        IFNULL(vyruchka_uspeh_payTabs.vyruchka_v_statuse_1_payTabs, 0) - IFNULL(vosvraty_payTabs.vozvraty_payTabs, 0) AS 'revenue_paytabs',
        IFNULL(vyruchka_uspeh_payTabs_ni.vyruchka_v_statuse_1_payTabs_ni, 0) - IFNULL(vozvraty_payTabs_ni.vozvraty_payTabs_ni, 0) AS 'total_paytabs',
        IFNULL(uspeh_Stripe.uspeh_Stripe, 0) - IFNULL(vozvraty_Stripe.vozvraty_Stripe, 0) AS 'revenue_stripe',
        IFNULL(uspeh_Stripe_ni.uspeh_Stripe_ni, 0) - IFNULL(vozvraty_Stripe_ni.vozvraty_Stripe_ni, 0) AS 'total_stripe',
        IFNULL(vyruchka_uspeh_payTabs.vyruchka_v_statuse_1_payTabs_ni, 0) - IFNULL(vosvraty_payTabs.vozvraty_payTabs_ni, 0) + IFNULL(uspeh_Stripe_ni.uspeh_Stripe_ni, 0) - IFNULL(vozvraty_Stripe_ni.vozvraty_Stripe_ni, 0) AS 'total_paytabs_plus_total_stripe',
        IFNULL(kvt.kvt, 0) AS 'kvt',
        IFNULL(user_v_den_register.user_v_den_register, 0) AS 'user_per_day',
        IFNULL(user_v_den_register.user_v_den_register_ni, 0) AS 'user_total',
        IFNULL(three_left_cols.obschee_vremya_min, 0) AS 'total_time_min',
        IFNULL(three_left_cols.obschee_vremya_min, 0) / IFNULL(three_left_cols.poezdok, 0) AS 'avg_time_of_ride',
        IFNULL(kolichestvo_novyh_s_1_poezdkoy.kolichestvo_novyh_s_1_poezdkoy, 0) AS 'count_rides_of_new_user_who_reg_today',
        IFNULL(kolichestvo_novyh_s_1_poezdkoy.kolichestvo_poezdok_vsego, 0) AS 'total_count_rides_of_new_user_who_reg_today',
        ROUND((kolichestvo_novyh_s_1_poezdkoy.kolichestvo_novyh_s_1_poezdkoy / user_v_den_register.user_v_den_register) * 100, 2) AS 'pervasion',
        ROUND(kolichestvo_novyh_s_1_poezdkoy.kolichestvo_poezdok_vsego / kolichestvo_novyh_s_1_poezdkoy.kolichestvo_novyh_s_1_poezdkoy, 2) AS 'count_rides_per_count_new_users'
    FROM t_city_with_noname
    left JOIN kvt ON t_city_with_noname.start_day = kvt.start_time AND t_city_with_noname.id = kvt.city_id
    LEFT JOIN sum_uspeh_abon ON t_city_with_noname.start_day = sum_uspeh_abon.start_time AND t_city_with_noname.id = sum_uspeh_abon.city_id
    LEFT JOIN sum_mnogor_abon ON t_city_with_noname.start_day = sum_mnogor_abon.start_time AND t_city_with_noname.id = sum_mnogor_abon.city_id
    left JOIN vyruchka_uspeh_payTabs ON t_city_with_noname.start_day = vyruchka_uspeh_payTabs.start_time AND t_city_with_noname.id = vyruchka_uspeh_payTabs.city_id
    LEFT JOIN vyruchka_uspeh_payTabs_ni ON t_city_with_noname.start_day = vyruchka_uspeh_payTabs_ni.start_time AND t_city_with_noname.id = vyruchka_uspeh_payTabs_ni.city_id
    LEFT JOIN vosvraty_payTabs ON t_city_with_noname.start_day = vosvraty_payTabs.start_time AND t_city_with_noname.id = vosvraty_payTabs.city_id
    LEFT JOIN vozvraty_payTabs_ni ON t_city_with_noname.start_day = vozvraty_payTabs_ni.start_time AND t_city_with_noname.id = vozvraty_payTabs_ni.city_id
    LEFT JOIN uspeh_Stripe ON t_city_with_noname.start_day = uspeh_Stripe.start_time AND t_city_with_noname.id = uspeh_Stripe.city_id
    LEFT JOIN uspeh_Stripe_ni ON t_city_with_noname.start_day = uspeh_Stripe_ni.start_time AND t_city_with_noname.id = uspeh_Stripe_ni.city_id
    LEFT JOIN vozvraty_Stripe ON t_city_with_noname.start_day = vozvraty_Stripe.start_time AND t_city_with_noname.id = vozvraty_Stripe.city_id
    LEFT JOIN vozvraty_Stripe_ni ON t_city_with_noname.start_day = vozvraty_Stripe_ni.start_time AND t_city_with_noname.id = vozvraty_Stripe_ni.city_id
    LEFT JOIN user_v_den_register ON t_city_with_noname.start_day = user_v_den_register.start_time AND t_city_with_noname.id = user_v_den_register.city_id 
    LEFT JOIN kolichestvo_novyh_s_1_poezdkoy ON t_city_with_noname.start_day = kolichestvo_novyh_s_1_poezdkoy.start_date AND t_city_with_noname.id = kolichestvo_novyh_s_1_poezdkoy.city_id
    LEFT JOIN dolgi ON t_city_with_noname.start_day = dolgi.create_debit_date AND t_city_with_noname.id = dolgi.city_id
    LEFT JOIN three_left_cols ON t_city_with_noname.start_day = three_left_cols.start_time AND t_city_with_noname.id = three_left_cols.city_id
    WHERE t_city_with_noname.start_day = DATE_FORMAT(NOW(), '%%Y-%%m-%%d')
    '''
    engine_mysql = f"mysql+pymysql://{user_mysql}:{p_mysql}@{host_mysql}:{port_mysql}/{db_mysql}"
    df_vni = pd.read_sql(select, engine_mysql)

    # Загрузка за сегодня в Postgres
    engine_postgresql = create_engine(f"mysql+pymysql://{user_postgres}:{password_postgres}@{host_postgres}:{port_postgres}/{db_postgres}")
    df_vni.to_sql('vni_cities', engine_postgresql, if_exists='append', index=False)

if __name__ == "__main__":
    main()
