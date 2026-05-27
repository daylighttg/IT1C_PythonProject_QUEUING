# Queue System Pseudocode

This document describes the queue system business logic in pseudocode form. It matches the behavior implemented by `source/core/queue_logic.py` and the underlying repository layer.

## Status Constants

- `WAITING_STATUS = "**waiting**"
- `SERVING_STATUS = "**serving**"
- `DONE_STATUS = "**done**"
- `TICKET_PREFIX = "**Q**"
- `TICKET_NUMBER_WIDTH = **3**
---
## Repository Interface

The queue service depends on a repository that supports these operations:

- `enqueue_customer(name, status, prefix, width) -> ticket`
- `get_first_by_status(status) -> record | None`
- `any_with_status(status) -> bool`
- `update_status(id, status) -> None`
- `list_waiting(status) -> list`
- `get_serving(status) -> row | None`
- `list_history() -> list`
- `list_all_records() -> list`
- `count_by_status(status) -> int`
- `status_counts() -> list[(status, count)]`
- `customer_id_by_ticket(ticket) -> id | None`
- `count_waiting_before(id, status) -> int`
- `record_by_id(id) -> (ticket, name) | None`
- `delete_by_id(id) -> None`
- `count_records() -> int`
- `clear_all_records() -> None`
- `exists_waiting_name(name, status) -> bool`
---
## Common Validation

```pseudocode
function validate_name(name):
    if type(name) is not string:
        raise QueueError("Customer name must be a string.")
    normalized = name.strip()
    if normalized is empty:
        raise QueueError("Customer name cannot be empty.")
    return normalized

function validate_ticket(ticket):
    if type(ticket) is not string:
        raise QueueError("Ticket must be a string.")
    normalized = ticket.strip()
    if normalized is empty:
        raise QueueError("Ticket cannot be empty.")
    return normalized

function validate_record_id(record_id):
    if type(record_id) is not int or type(record_id) is bool:
        raise QueueError("Record ID must be an integer.")
    if record_id <= 0:
        raise QueueError("Record ID must be greater than zero.")
    return record_id
```
---
## Join Queue

```pseudocode
function join_queue(customer_name):
    validated_name = validate_name(customer_name)

    if duplicates_are_not_allowed and repository.exists_waiting_name(validated_name, WAITING_STATUS):
        raise QueueError(validated_name + " is already waiting in the queue.")

    ticket = repository.enqueue_customer(
        validated_name,
        WAITING_STATUS,
        TICKET_PREFIX,
        TICKET_NUMBER_WIDTH,
    )

    return ticket
```
---
## Call Next Customer

```pseudocode
function call_next():
    if repository.any_with_status(SERVING_STATUS):
        raise QueueFullError("A customer is already being served. Mark them as done first.")

    next_customer = repository.get_first_by_status(WAITING_STATUS)
    if next_customer is None:
        return None

    id, ticket, name = next_customer
    repository.update_status(id, SERVING_STATUS)
    return (ticket, name)
```
---
## Mark Current Customer Done

```pseudocode
function mark_done():
    serving_customer = repository.get_first_by_status(SERVING_STATUS)
    if serving_customer is None:
        return None

    id, ticket, name = serving_customer
    repository.update_status(id, DONE_STATUS)
    return (ticket, name)
```
---
## Query Functions

```pseudocode
function get_waiting():
    return repository.list_waiting(WAITING_STATUS)

function get_serving():
    return repository.get_serving(SERVING_STATUS)

function get_history():
    return repository.list_history()

function get_all_records():
    return repository.list_all_records()

function count_waiting():
    return repository.count_by_status(WAITING_STATUS)
```
---
## Statistics
---
```pseudocode
function get_stats():
    counts = {
        WAITING_STATUS: 0,
        SERVING_STATUS: 0,
        DONE_STATUS: 0,
    }
    total = 0

    for status, count in repository.status_counts():
        total += count
        if status in counts:
            counts[status] = count

    counts["total"] = total
    return counts
```
---
## Get Waiting Position

```pseudocode
function get_waiting_position(ticket):
    validated_ticket = validate_ticket(ticket)
    customer_id = repository.customer_id_by_ticket(validated_ticket)
    if customer_id is None:
        return 0
    return repository.count_waiting_before(customer_id, WAITING_STATUS)
```
---
## Delete Record

```pseudocode
function delete_record(record_id):
    validated_id = validate_record_id(record_id)
    record = repository.record_by_id(validated_id)
    if record is None:
        return None

    repository.delete_by_id(validated_id)
    return record
```

## Clear All Records

```pseudocode
function clear_all_records():
    total = repository.count_records()
    if total > 0:
        repository.clear_all_records()
    return total
```

## Exported Service Functions

The module exposes helper functions that call the shared queue service instance:

- `join_queue(name)`
- `call_next()`
- `mark_done()`
- `get_waiting()`
- `get_serving()`
- `get_history()`
- `get_all_records()`
- `count_waiting()`
- `get_stats()`
- `get_waiting_position(ticket)`
- `delete_record(record_id)`
- `clear_all_records()`
