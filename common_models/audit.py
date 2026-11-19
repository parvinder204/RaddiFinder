from .models import AuditLog, PickupItems


def record(actor, action, target_type, target_id, snapshot=None):
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        snapshot=snapshot or {},
    )


def pickup_item_snapshot(row):
    return {
        "id": str(row.pk),
        "pickup_id": str(row.pickup_id),
        "item_id": str(row.item_id),
        "item_reference": row.item.reference,
        "item": row.item.name,
        "quantity": row.quantity,
        "actual_quantity": row.actual_quantity,
        "final_price": row.final_price,
    }


def pickup_snapshot(pickup):
    rows = PickupItems.objects.filter(pickup=pickup).select_related("item")
    return {
        "pickup_id": str(pickup.pickup_id),
        "reference": pickup.reference,
        "customer_id": str(pickup.customer_id),
        "customer_phone": pickup.customer.phone,
        "status": pickup.status,
        "pickup_date": pickup.pickup_date,
        "time_slot": pickup.time_slot,
        "address": pickup.address,
        "city": pickup.city.name if pickup.city else None,
        "state": pickup.state.name if pickup.state else None,
        "pin_code": pickup.pin_code,
        "pickup_boy": str(pickup.pickup_boy) if pickup.pickup_boy_id else None,
        "payment": pickup.payment,
        "notes": pickup.notes,
        "additional_data": pickup.additional_data,
        "items": [pickup_item_snapshot(row) for row in rows],
    }
