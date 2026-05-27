

## 1. DATABASE MODULE (`core/database.py`)

```
FUNCTION initialize_database():
    CONNECT to SQLite file "queue_system.db"
    
    IF table "queue" does NOT exist THEN
        CREATE TABLE queue WITH columns:
            - id          : INTEGER, PRIMARY KEY, auto-increment
            - ticket_no   : TEXT, unique ticket identifier
            - name        : TEXT, customer name
            - status      : TEXT  ("waiting" | "serving" | "done")
            - joined_at   : DATETIME, timestamp when customer joined
            - called_at   : DATETIME, timestamp when customer was called
            - done_at     : DATETIME, timestamp when service completed
    END IF
    
    RETURN database connection
END FUNCTION
```

---

## 2. QUEUE LOGIC MODULE (`core/queue_logic.py`)

### 2a. Join Queue

```
FUNCTION join_queue(name):
    IF name is empty or blank THEN
        RAISE InvalidNameException("Name cannot be empty")
    END IF

    ticket_no  ← GENERATE ticket (e.g., "T-001", auto-incremented)
    joined_at  ← CURRENT timestamp
    status     ← "waiting"

    INSERT record (ticket_no, name, status, joined_at) INTO queue table

    RETURN ticket_no
END FUNCTION
```

### 2b. Call Next Customer

```
FUNCTION call_next():
    IF any customer currently has status = "serving" THEN
        RAISE QueueBusyException("Finish current customer before calling next")
    END IF

    next_customer ← SELECT first record WHERE status = "waiting"
                    ORDER BY joined_at ASC

    IF next_customer does NOT exist THEN
        RAISE EmptyQueueException("No customers are waiting")
    END IF

    called_at ← CURRENT timestamp
    UPDATE next_customer SET status = "serving", called_at = called_at

    RETURN next_customer
END FUNCTION
```

### 2c. Mark Customer as Done

```
FUNCTION mark_done():
    current_customer ← SELECT record WHERE status = "serving"

    IF current_customer does NOT exist THEN
        RAISE NoServingCustomerException("No customer is currently being served")
    END IF

    done_at ← CURRENT timestamp
    UPDATE current_customer SET status = "done", done_at = done_at

    RETURN current_customer
END FUNCTION
```

### 2d. View Waiting Queue

```
FUNCTION get_waiting_queue():
    records ← SELECT all records WHERE status = "waiting"
               ORDER BY joined_at ASC

    RETURN records   // empty list if no one is waiting
END FUNCTION
```

### 2e. Get Queue Status

```
FUNCTION get_status():
    serving_customer ← SELECT record WHERE status = "serving"
    waiting_count    ← COUNT records WHERE status = "waiting"

    RETURN {
        "serving"       : serving_customer (or None),
        "waiting_count" : waiting_count
    }
END FUNCTION
```

### 2f. View Full History

```
FUNCTION get_history():
    records ← SELECT all records FROM queue table
               ORDER BY joined_at DESC

    RETURN records
END FUNCTION
```

### 2g. Delete a Record

```
FUNCTION delete_record(record_id):
    IF record with record_id does NOT exist THEN
        RAISE RecordNotFoundException("Record not found")
    END IF

    DELETE record WHERE id = record_id
    RETURN success message
END FUNCTION
```

### 2h. Clear All Records

```
FUNCTION clear_all_records():
    DELETE all records FROM queue table
    RESET auto-increment counter

    RETURN success message
END FUNCTION
```

---

## 3. COMMAND-LINE INTERFACE (`main.py`)

```
FUNCTION main():
    CALL initialize_database()

    LOOP forever:
        DISPLAY menu:
            [1] Join Queue
            [2] Call Next Customer
            [3] Mark Customer as Done
            [4] View Waiting Queue
            [5] View Full History
            [6] Delete a Record
            [7] Clear All Records
            [0] Exit

        choice ← GET user input

        MATCH choice:

            CASE 1:
                name ← GET user input ("Enter customer name: ")
                TRY
                    ticket ← join_queue(name)
                    DISPLAY "Joined! Your ticket number is: " + ticket
                CATCH InvalidNameException as e:
                    DISPLAY "Error: " + e.message
                END TRY

            CASE 2:
                TRY
                    customer ← call_next()
                    DISPLAY "Now serving: " + customer.name
                             + " (Ticket: " + customer.ticket_no + ")"
                CATCH QueueBusyException, EmptyQueueException as e:
                    DISPLAY "Error: " + e.message
                END TRY

            CASE 3:
                TRY
                    customer ← mark_done()
                    DISPLAY "Done serving: " + customer.name
                CATCH NoServingCustomerException as e:
                    DISPLAY "Error: " + e.message
                END TRY

            CASE 4:
                queue ← get_waiting_queue()
                IF queue is empty THEN
                    DISPLAY "No customers are waiting."
                ELSE
                    FOR each customer IN queue:
                        DISPLAY customer.ticket_no + " | " + customer.name
                              + " | Joined: " + customer.joined_at
                    END FOR
                END IF

            CASE 5:
                history ← get_history()
                IF history is empty THEN
                    DISPLAY "No records found."
                ELSE
                    FOR each record IN history:
                        DISPLAY record.id + " | " + record.ticket_no
                              + " | " + record.name + " | " + record.status
                    END FOR
                END IF

            CASE 6:
                record_id ← GET user input ("Enter record ID to delete: ")
                TRY
                    delete_record(record_id)
                    DISPLAY "Record deleted successfully."
                CATCH RecordNotFoundException as e:
                    DISPLAY "Error: " + e.message
                END TRY

            CASE 7:
                confirm ← GET user input ("Clear ALL records? (yes/no): ")
                IF confirm = "yes" THEN
                    clear_all_records()
                    DISPLAY "All records cleared."
                ELSE
                    DISPLAY "Operation cancelled."
                END IF

            CASE 0:
                DISPLAY "Goodbye!"
                EXIT loop

            DEFAULT:
                DISPLAY "Invalid choice. Please try again."
        END MATCH
    END LOOP
END FUNCTION

CALL main()
```

---

## 4. REST API SERVER (`api/server.py`)

```
FUNCTION start_api_server():
    CALL initialize_database()
    CREATE Flask app

    // ── POST /join ──────────────────────────────────────────────
    ENDPOINT POST "/join":
        body ← PARSE JSON request body
        name ← body["name"]

        TRY
            ticket ← join_queue(name)
            RETURN JSON { "ticket_no": ticket, "message": "Joined queue" }, status 201
        CATCH InvalidNameException as e:
            RETURN JSON { "error": e.message }, status 400
        END TRY

    // ── GET /queue ───────────────────────────────────────────────
    ENDPOINT GET "/queue":
        waiting ← get_waiting_queue()
        RETURN JSON list of waiting customers, status 200

    // ── GET /status ──────────────────────────────────────────────
    ENDPOINT GET "/status":
        status ← get_status()
        RETURN JSON {
            "serving"       : status.serving,
            "waiting_count" : status.waiting_count
        }, status 200

    // ── POST /next ───────────────────────────────────────────────
    ENDPOINT POST "/next":
        TRY
            customer ← call_next()
            RETURN JSON { "now_serving": customer }, status 200
        CATCH QueueBusyException, EmptyQueueException as e:
            RETURN JSON { "error": e.message }, status 400
        END TRY

    // ── POST /done ───────────────────────────────────────────────
    ENDPOINT POST "/done":
        TRY
            customer ← mark_done()
            RETURN JSON { "completed": customer }, status 200
        CATCH NoServingCustomerException as e:
            RETURN JSON { "error": e.message }, status 400
        END TRY

    // ── GET /history ─────────────────────────────────────────────
    ENDPOINT GET "/history":
        history ← get_history()
        RETURN JSON list of all records, status 200

    RUN Flask app on host="0.0.0.0", port=5000
END FUNCTION

CALL start_api_server()
```

---

## 5. CUSTOM EXCEPTIONS (`core/exceptions.py`)

```
CLASS InvalidNameException        EXTENDS Exception
CLASS EmptyQueueException         EXTENDS Exception
CLASS QueueBusyException          EXTENDS Exception
CLASS NoServingCustomerException  EXTENDS Exception
CLASS RecordNotFoundException     EXTENDS Exception
```

---

## 6. SYSTEM FLOW SUMMARY

```
START
  │
  ▼
Initialize Database (create tables if needed)
  │
  ▼
User selects interface:
  ├── CLI  ──► Show Menu ──► User picks action
  └── API  ──► Listen on port 5000 ──► Receive HTTP request
                                          │
                            ┌────────────▼─────────────┐
                            │    Core Queue Logic       │
                            │  (queue_logic.py)         │
                            │                           │
                            │  join_queue()             │
                            │  call_next()              │
                            │  mark_done()              │
                            │  get_waiting_queue()      │
                            │  get_status()             │
                            │  get_history()            │
                            │  delete_record()          │
                            │  clear_all_records()      │
                            └────────────┬─────────────┘
                                         │
                            ┌────────────▼─────────────┐
                            │    SQLite Database        │
                            │  (queue_system.db)        │
                            └──────────────────────────┘
END
```

---

*Generated from: https://github.com/aira112507/IT1C_PythonProject_QUEUING*
