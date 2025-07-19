import asyncio
import websockets
import json
from datetime import datetime, timedelta

connected_clients = {}  # name -> websocket
answers = {}
WAITING_ROOM_DURATION = 30
QUESTION_DURATION = 20

QUESTION = {
    "type": "question",
    "question": "What is 2 + 2?",
    "options": [2, 3, 4, 5],
    "correct_answer": "4"
}

game_started = asyncio.Event()

async def handler(websocket):
    await websocket.send(json.dumps({"type": "waiting_room", "message": "Game starting soon! Please enter your name."}))
    name = await websocket.recv()
    connected_clients[name] = websocket
    print(f"{name} joined the game.")

    # Wait for the game to start
    await game_started.wait()

    # Wait for question
    await websocket.send(json.dumps({
        "type": "question",
        "question": QUESTION["question"],
        "options": QUESTION["options"]
    }))

    # Receive answer
    try:
        msg = await asyncio.wait_for(websocket.recv(), timeout=QUESTION_DURATION)
        msg_data = json.loads(msg)
        if msg_data.get("type") == "answer":
            answers[name] = msg_data["answer"]
            print(f"Answer from {name}: {answers[name]}")
    except asyncio.TimeoutError:
        print(f"{name} did not answer in time.")

async def start_game():
    print(f"Waiting for players ({WAITING_ROOM_DURATION} sec)...")
    await asyncio.sleep(WAITING_ROOM_DURATION)
    print("Game starting!")
    game_started.set()  # Signal all clients to proceed
    await asyncio.sleep(QUESTION_DURATION + 1)  # Allow time for answers
    await announce_winner()

async def announce_winner():
    correct_players = [name for name, ans in answers.items() if ans == QUESTION["correct_answer"]]
    winner_message = (
        f"Winner(s): {', '.join(correct_players)}"
        if correct_players else
        "No one answered correctly!"
    )
    result_payload = {"type": "result", "message": winner_message}

    for name, ws in list(connected_clients.items()):
        if ws.closed:
            print(f"Skipping {name} (connection already closed).")
            continue
        try:
            await ws.send(json.dumps(result_payload))
        except Exception as e:
            print(f"Failed to send result to {name}: {e}")

    print(winner_message)

async def main():
    server = await websockets.serve(handler, "localhost", 6789)
    await start_game()
    server.close()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())