# Queue System Pseudocode


---

## 1. DATABASE MODULE (`core/database.py`)

```
FUNCTION create_tables():
    CONNECT to SQLite file "queue_system.db"
    CREATE TABLE customers IF NOT EXISTS with columns:
        - id         : INTEGER, PRIMARY KEY, auto-increment
        - ticket     : TEXT, generated ticket (Q###)
        - name       : TEXT, customer name
        - status     : TEXT  (waiting | serving | done)
        - priority   : INTEGER (0=Regular, 1=Priority, 2=VIP)
        - created_at : TIMESTAMP default CURRENT_TIMESTAMP
    CLOSE connection
END FUNCTION

FUNCTION enqueue_customer(name, waiting_status, ticket_prefix, ticket_width, priority):
    INSERT record with empty ticket
    ticket_id ← last inserted row id
    ticket    ← ticket_prefix + zero_pad(ticket_id, ticket_width)
    UPDATE record with generated ticket
    RETURN ticket
END FUNCTION
```

---

## 2. QUEUE LOGIC MODULE (`core/queue_logic.py`)

### 2a. Join Queue

```
FUNCTION join_queue(name, priority=0):
    VALIDATE name is non-empty string
    VALIDATE priority in {0,1,2}
    IF duplicate waiting names are blocked AND name already waiting THEN
        RAISE QueueError
    END IF

    ticket ← enqueue_customer(name, "waiting", "Q", 3, priority)
    RETURN ticket
END FUNCTION
```

### 2b. Call Next Customer (Priority + Time Decay)

```
FUNCTION call_next():
    IF any customer has status = "serving" THEN
        RAISE QueueFullError("already serving")
    END IF

    waiting_rows ← list_waiting("waiting")  // (ticket, name, created_at, priority)
    IF waiting_rows is empty THEN
        RETURN None
    END IF

    FOR each row IN waiting_rows:
        waited_seconds ← now - parse_time(created_at)
        IF waited_seconds >= 600 THEN
            effective_priority ← min(priority + 1, 2)
        ELSE
            effective_priority ← priority
        END IF
    END FOR

    ORDER rows by effective_priority DESC, created_at ASC
    next_ticket ← first row.ticket
    UPDATE that row status -> "serving"
    RETURN (next_ticket, name)
END FUNCTION
```

### 2c. Mark Customer as Done

```
FUNCTION mark_done():
    serving_row ← first row WHERE status = "serving"
    IF serving_row does NOT exist THEN
        RETURN None
    END IF
    UPDATE serving_row status -> "done"
    RETURN (ticket, name)
END FUNCTION
```

### 2d. Waiting, History, Stats, and Utilities

```
FUNCTION get_waiting():
    RETURN list_waiting("waiting")  // ordered by priority DESC, created_at ASC
END FUNCTION

FUNCTION get_serving():
    RETURN current serving row or None
END FUNCTION

FUNCTION get_history():
    RETURN all rows ordered by id ASC
END FUNCTION

FUNCTION get_stats():
    RETURN counts for waiting, serving, done, plus total
END FUNCTION

FUNCTION get_waiting_position(ticket):
    RETURN number of waiting customers ahead of ticket
END FUNCTION

FUNCTION edit_record(record_id, priority):
    VALIDATE record_id and priority
    UPDATE record priority
    RETURN (ticket, name) or None if missing
END FUNCTION

FUNCTION delete_record(record_id):
    DELETE record by id
    RETURN (ticket, name) or None if missing
END FUNCTION

FUNCTION clear_all_records():
    DELETE all rows
    RETURN count deleted
END FUNCTION
```

---

## 3. GUI APPLICATION (`main.py`)

```
FUNCTION main():
    create_tables()
    START Tkinter app

    UI actions:
        Join Queue         -> join_queue(name, priority)
        Call Next          -> call_next()
        Mark Done          -> mark_done()
        Edit Record        -> edit_record(record_id, priority)
        Delete Record      -> delete_record(record_id)
        Clear All Records  -> clear_all_records()
        Refresh            -> get_waiting(), get_history(), get_stats()

    OPTIONAL:
        Start/Stop Flask server (subprocess)
END FUNCTION
```

---

## 4. REST API SERVER (`api/server.py`)

```
FUNCTION start_api_server():
    create_tables()
    READ ADMIN_API_KEY from environment (default: "changeme")
    CREATE Flask app

    ENDPOINT POST "/join":
        body ← JSON
        name ← body["name"]
        priority ← body.get("priority", 0)
        ticket ← join_queue(name, priority)
        position ← get_waiting_position(ticket)
        RETURN {ticket, name, priority, position}, status 201

    ENDPOINT GET "/queue":
        waiting ← get_waiting()
        RETURN {waiting: [...], count: N}

    ENDPOINT GET "/status":
        serving ← get_serving()
        waiting_count ← count_waiting()
        RETURN {serving, waiting: waiting_count}

    ENDPOINT POST "/next" (requires X-API-Key):
        result ← call_next()
        RETURN {ticket, name} OR error

    ENDPOINT POST "/done" (requires X-API-Key):
        result ← mark_done()
        RETURN {ticket, name} OR error

    ENDPOINT GET "/history":
        history ← get_history()
        RETURN {records: [...], count: N}
END FUNCTION
```

---

## 5. CUSTOM EXCEPTIONS (`core/exceptions.py`)

```
CLASS QueueError        EXTENDS RuntimeError
CLASS QueueFullError    EXTENDS QueueError
CLASS QueueEmptyError   EXTENDS QueueError
CLASS DatabaseError     EXTENDS QueueError
CLASS PriorityError     EXTENDS QueueError
```

---

## 6. SYSTEM FLOW SUMMARY

```
START
  |
  v
Create DB tables
  |
  v
User chooses entry point:
  - GUI  -> Tkinter UI actions
  - API  -> Flask server endpoints
  |
  v
Core queue logic (priority + time decay)
  |
  v
SQLite database
END
```

