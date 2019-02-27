from flask import current_app
from notifications_utils.statsd_decorators import statsd
from sqlalchemy import desc, and_
from sqlalchemy.orm import aliased

from app import db
from app.dao.dao_utils import transactional
from app.models import InboundSms, Service, ServiceDataRetention, SMS_TYPE
from app.utils import midnight_n_days_ago


@transactional
def dao_create_inbound_sms(inbound_sms):
    db.session.add(inbound_sms)


def dao_get_inbound_sms_for_service(service_id, limit=None, user_number=None, days_ago_to_start=6):
    q = InboundSms.query.filter(
        InboundSms.service_id == service_id
    ).order_by(
        InboundSms.created_at.desc()
    )
    if days_ago_to_start is not None:
        start_date = midnight_n_days_ago(days_ago_to_start)
        q = q.filter(InboundSms.created_at >= start_date)

    if user_number:
        q = q.filter(InboundSms.user_number == user_number)

    if limit:
        q = q.limit(limit)

    return q.all()


def dao_get_paginated_inbound_sms_for_service_for_public_api(
    service_id,
    older_than=None,
    page_size=None
):
    if page_size is None:
        page_size = current_app.config['PAGE_SIZE']

    filters = [InboundSms.service_id == service_id]

    if older_than:
        older_than_created_at = db.session.query(
            InboundSms.created_at).filter(InboundSms.id == older_than).as_scalar()
        filters.append(InboundSms.created_at < older_than_created_at)

    query = InboundSms.query.filter(*filters)

    return query.order_by(desc(InboundSms.created_at)).paginate(
        per_page=page_size
    ).items


def dao_count_inbound_sms_for_service(service_id):
    start_date = midnight_n_days_ago(6)
    return InboundSms.query.filter(
        InboundSms.service_id == service_id,
        InboundSms.created_at >= start_date
    ).count()


def _delete_inbound_sms(datetime_to_delete_from, query_filter):
    query_limit = 10000

    subquery = db.session.query(
        InboundSms.id
    ).filter(
        InboundSms.created_at < datetime_to_delete_from,
        *query_filter
    ).limit(
        query_limit
    ).subquery()

    deleted = 0
    # set to nonzero just to enter the loop
    number_deleted = 1
    while number_deleted > 0:
        number_deleted = InboundSms.query.filter(InboundSms.id.in_(subquery)).delete(synchronize_session='fetch')
        deleted += number_deleted

    return deleted


@statsd(namespace="dao")
@transactional
def delete_inbound_sms_older_than_retention():
    current_app.logger.info('Deleting inbound sms for services with flexible data retention')

    flexible_data_retention = ServiceDataRetention.query.join(
        ServiceDataRetention.service,
        Service.inbound_number
    ).filter(
        ServiceDataRetention.notification_type == SMS_TYPE
    ).all()

    deleted = 0
    for f in flexible_data_retention:
        n_days_ago = midnight_n_days_ago(f.days_of_retention)

        current_app.logger.info("Deleting inbound sms for service id: {}".format(f.service_id))
        deleted += _delete_inbound_sms(n_days_ago, query_filter=[InboundSms.service_id == f.service_id])

    current_app.logger.info('Deleting inbound sms for services without flexible data retention')

    seven_days_ago = midnight_n_days_ago(7)

    deleted += _delete_inbound_sms(seven_days_ago, query_filter=[
        InboundSms.service_id.notin_(x.service_id for x in flexible_data_retention),
    ])

    current_app.logger.info('Deleted {} inbound sms'.format(deleted))

    return deleted


def dao_get_inbound_sms_by_id(service_id, inbound_id):
    return InboundSms.query.filter_by(
        id=inbound_id,
        service_id=service_id
    ).one()


def dao_get_paginated_most_recent_inbound_sms_by_user_number_for_service(
    service_id,
    page
):
    """
    This query starts from inbound_sms and joins on to itself to find the most recent row for each user_number

    Equivalent sql:

    SELECT t1.*
    FROM inbound_sms t1
    LEFT OUTER JOIN inbound_sms AS t2 ON (
        -- identifying
        t1.user_number = t2.user_number AND
        t1.service_id = t2.service_id AND
        -- ordering
        t1.created_at < t2.created_at
    )
    WHERE t2.id IS NULL AND t1.service_id = :service_id
    ORDER BY t1.created_at DESC;
    LIMIT 50 OFFSET :page
    """
    start_date = midnight_n_days_ago(6)
    t2 = aliased(InboundSms)
    q = db.session.query(
        InboundSms
    ).outerjoin(
        t2,
        and_(
            InboundSms.user_number == t2.user_number,
            InboundSms.service_id == t2.service_id,
            InboundSms.created_at < t2.created_at,
        )
    ).filter(
        t2.id == None,  # noqa
        InboundSms.service_id == service_id,
        InboundSms.created_at >= start_date
    ).order_by(
        InboundSms.created_at.desc()
    )

    return q.paginate(
        page=page,
        per_page=current_app.config['PAGE_SIZE']
    )
