"""Evaluation metrics calculator.

Computes precision, recall, F1 per class, macro-F1, accuracy,
and the notify False Positive Rate against golden labels.
"""

import logging

from app.schemas.message import BatchEvalResponse, ClassMetrics

logger = logging.getLogger(__name__)

CLASSES = ["notify", "digest", "mute"]


def calculate_metrics(
    predictions: list[dict],
    golden: list[dict],
) -> BatchEvalResponse:
    """Calculate evaluation metrics by comparing predictions to golden labels.

    Args:
        predictions: List of dicts with at least {message_id, action}
        golden: List of dicts with at least {message_id, action}

    Returns:
        BatchEvalResponse with full metrics
    """
    # Build lookup: message_id -> dict
    pred_map = {p["message_id"]: p.get("action", "digest") for p in predictions}
    gold_map = {g["message_id"]: g for g in golden}

    # Find common message IDs
    common_ids = set(pred_map.keys()) & set(gold_map.keys())
    if not common_ids:
        logger.warning("No overlapping message IDs between predictions and golden labels")
        return BatchEvalResponse(
            total_processed=len(predictions),
            accuracy=0.0,
            macro_f1=0.0,
            notify_fpr=0.0,
            class_metrics={},
        )

    # Count TP, FP, FN per class
    tp: dict[str, int] = {c: 0 for c in CLASSES}
    fp: dict[str, int] = {c: 0 for c in CLASSES}
    fn: dict[str, int] = {c: 0 for c in CLASSES}
    correct = 0

    for msg_id in common_ids:
        pred = pred_map[msg_id]
        gold_action = gold_map[msg_id].get("action", "")

        if pred == gold_action:
            correct += 1
            if pred in tp:
                tp[pred] += 1
        else:
            if pred in fp:
                fp[pred] += 1
            if gold_action in fn:
                fn[gold_action] += 1

    # Calculate per-class metrics
    class_metrics: dict[str, ClassMetrics] = {}
    f1_scores = []

    for c in CLASSES:
        precision = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) > 0 else 0.0
        recall = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        support = tp[c] + fn[c]  # True instances of this class

        class_metrics[c] = ClassMetrics(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            support=support,
        )
        f1_scores.append(f1)

    # Macro F1
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    # Accuracy
    accuracy = correct / len(common_ids) if common_ids else 0.0

    # P2: Stratified accuracy by message_type
    # {message_type: {"correct": int, "total": int}}
    type_stats: dict[str, dict[str, int]] = {}
    for msg_id in common_ids:
        gold_type = gold_map[msg_id].get("message_type", "unknown")
        if gold_type not in type_stats:
            type_stats[gold_type] = {"correct": 0, "total": 0}
        type_stats[gold_type]["total"] += 1
        if pred_map[msg_id] == gold_map[msg_id]["action"]:
            type_stats[gold_type]["correct"] += 1

    per_type_accuracy = {}
    for mtype, stats in type_stats.items():
        if stats["total"] > 0:
            per_type_accuracy[mtype] = round(stats["correct"] / stats["total"], 4)

    # Notify False Positive Rate = FP_notify / (FP_notify + TN_notify)
    # TN_notify = total non-notify golds that were not predicted as notify
    total_non_notify_gold = sum(
        1 for mid in common_ids if gold_map[mid]["action"] != "notify"
    )
    notify_fpr = (
        fp["notify"] / total_non_notify_gold
        if total_non_notify_gold > 0
        else 0.0
    )

    # Confusion matrix: {gold_action: {pred_action: count}}
    confusion: dict[str, dict[str, int]] = {c: {c2: 0 for c2 in CLASSES} for c in CLASSES}
    for msg_id in common_ids:
        pred = pred_map[msg_id]
        gold_action = gold_map[msg_id].get("action", "")
        if gold_action in confusion and pred in confusion[gold_action]:
            confusion[gold_action][pred] += 1

    return BatchEvalResponse(
        total_processed=len(predictions),
        accuracy=round(accuracy, 4),
        macro_f1=round(macro_f1, 4),
        notify_fpr=round(notify_fpr, 4),
        class_metrics=class_metrics,
        confusion_matrix=confusion,
        per_type_accuracy=per_type_accuracy,
    )
