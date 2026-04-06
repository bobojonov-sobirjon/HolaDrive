"""
Driver identification checklist: acceptance rules for list/detail APIs.
"""

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import (
    DriverIdentificationAgreementsItems,
    DriverIdentificationLegalAgreementsUserAccepted,
    DriverIdentificationLegalType,
    DriverIdentificationTermsItemUserAccepted,
    DriverIdentificationTermsType,
    DriverIdentificationUploadType,
    DriverIdentificationUploadTypeQuestionAnswer,
    DriverIdentificationUploadTypeUserAccepted,
)


def _upload_row_complete(row):
    if row is None or not row.is_accepted:
        return False
    name = getattr(row.file, 'name', '') if row.file else ''
    return bool(name)


def question_answer_ids_by_upload_type(upload_type_ids):
    if not upload_type_ids:
        return {}
    grouped = defaultdict(list)
    qs = (
        DriverIdentificationUploadTypeQuestionAnswer.objects.filter(
            driver_identification_upload_type_item__driver_identification_upload_type_id__in=upload_type_ids,
        )
        .values_list(
            'id',
            'driver_identification_upload_type_item__driver_identification_upload_type_id',
        )
        .order_by(
            'driver_identification_upload_type_item__created_at',
            'driver_identification_upload_type_item__id',
            'created_at',
            'id',
        )
    )
    for qid, tid in qs:
        grouped[tid].append(qid)
    return dict(grouped)


def upload_acceptance_maps(user_id, upload_type_ids):
    rows = DriverIdentificationUploadTypeUserAccepted.objects.filter(
        user_id=user_id,
        driver_identification_upload_type_id__in=upload_type_ids,
    )
    by_type_whole = {}
    by_qa = {}
    for r in rows:
        if r.question_answer_id is None:
            by_type_whole[r.driver_identification_upload_type_id] = r
        else:
            by_qa[r.question_answer_id] = r
    return by_type_whole, by_qa


def upload_type_is_accepted(type_id, qa_ids, by_type_whole, by_qa):
    if not qa_ids:
        return _upload_row_complete(by_type_whole.get(type_id))
    return all(_upload_row_complete(by_qa.get(qid)) for qid in qa_ids)


def pick_question_answer_id_for_submit(user_id, ordered_qa_ids):
    """
    When the client sends only upload_type_id + file, pick the checklist slot in admin order:
    first slot that is not yet complete; if all complete, replace the first slot.
    """
    if not ordered_qa_ids:
        return None
    if len(ordered_qa_ids) == 1:
        return ordered_qa_ids[0]
    rows = {
        r.question_answer_id: r
        for r in DriverIdentificationUploadTypeUserAccepted.objects.filter(
            user_id=user_id,
            question_answer_id__in=ordered_qa_ids,
        )
    }
    for qid in ordered_qa_ids:
        if not _upload_row_complete(rows.get(qid)):
            return qid
    return ordered_qa_ids[0]


def terms_content_type():
    return ContentType.objects.get_for_model(DriverIdentificationTermsType)


def terms_agreement_item_ids_by_type(terms_type_ids):
    if not terms_type_ids:
        return {}
    ct = terms_content_type()
    grouped = defaultdict(list)
    qs = (
        DriverIdentificationAgreementsItems.objects.filter(
            content_type=ct,
            object_id__in=terms_type_ids,
            item_type='terms',
        )
        .values_list('id', 'object_id')
        .order_by('created_at', 'id')
    )
    for aid, tid in qs:
        grouped[tid].append(aid)
    return dict(grouped)


def legal_content_type():
    return ContentType.objects.get_for_model(DriverIdentificationLegalType)


def terms_agreement_items(terms_type):
    ct = terms_content_type()
    return DriverIdentificationAgreementsItems.objects.filter(
        content_type=ct,
        object_id=terms_type.pk,
        item_type='terms',
    ).order_by('created_at', 'id')


def legal_agreement_items(legal_type):
    ct = legal_content_type()
    return DriverIdentificationAgreementsItems.objects.filter(
        content_type=ct,
        object_id=legal_type.pk,
        item_type='legal',
    ).order_by('created_at', 'id')


def terms_type_is_accepted(item_ids, accepted_item_ids_set):
    if not item_ids:
        return False
    return all(i in accepted_item_ids_set for i in item_ids)


def legal_acceptance_map(user_id, legal_type_ids):
    if not legal_type_ids:
        return {}
    rows = DriverIdentificationLegalAgreementsUserAccepted.objects.filter(
        user_id=user_id,
        driver_identification_legal_agreements_id__in=legal_type_ids,
    )
    return {r.driver_identification_legal_agreements_id: r.is_accepted for r in rows}


def build_checklist_payload(user):
    """Flat list: upload, terms, and legal steps sorted by created_at (then id, kind)."""
    user_id = user.pk

    uploads = list(
        DriverIdentificationUploadType.objects.filter(is_active=True, display_type='upload').order_by(
            'created_at', 'id'
        )
    )
    terms_list = list(
        DriverIdentificationTermsType.objects.filter(is_active=True, display_type='terms').order_by(
            'created_at', 'id'
        )
    )
    legals = list(
        DriverIdentificationLegalType.objects.filter(is_active=True, display_type='legal').order_by(
            'created_at', 'id'
        )
    )

    upload_ids = [u.pk for u in uploads]
    qa_by_type = question_answer_ids_by_upload_type(upload_ids)
    by_whole, by_qa = upload_acceptance_maps(user_id, upload_ids)

    legal_ids = [x.pk for x in legals]
    legal_acc = legal_acceptance_map(user_id, legal_ids)

    terms_ids = [x.pk for x in terms_list]
    items_by_terms = terms_agreement_item_ids_by_type(terms_ids)
    all_term_item_ids = [i for ids in items_by_terms.values() for i in ids]
    accepted_terms_items = set(
        DriverIdentificationTermsItemUserAccepted.objects.filter(
            user_id=user_id,
            agreement_item_id__in=all_term_item_ids,
            is_accepted=True,
        ).values_list('agreement_item_id', flat=True)
    )

    steps = []
    for u in uploads:
        qas = qa_by_type.get(u.pk, [])
        steps.append(
            (
                u.created_at,
                u.pk,
                'upload',
                {
                    'kind': 'upload',
                    'id': u.pk,
                    'title': u.title,
                    'is_accepted': upload_type_is_accepted(u.pk, qas, by_whole, by_qa),
                },
            )
        )
    for t in terms_list:
        item_ids = items_by_terms.get(t.pk, [])
        steps.append(
            (
                t.created_at,
                t.pk,
                'terms',
                {
                    'kind': 'terms',
                    'id': t.pk,
                    'title': t.title,
                    'is_accepted': terms_type_is_accepted(item_ids, accepted_terms_items),
                },
            )
        )
    for lg in legals:
        steps.append(
            (
                lg.created_at,
                lg.pk,
                'legal',
                {
                    'kind': 'legal',
                    'id': lg.pk,
                    'title': lg.title,
                    'is_accepted': bool(legal_acc.get(lg.pk, False)),
                },
            )
        )

    steps.sort(key=lambda x: (x[0], x[1], x[2]))
    return [s[3] for s in steps]


def apply_terms_acceptance(user, terms_type, is_accepted: bool):
    for item in terms_agreement_items(terms_type):
        DriverIdentificationTermsItemUserAccepted.objects.update_or_create(
            user=user,
            agreement_item=item,
            defaults={'is_accepted': is_accepted},
        )
