import threading

event = threading.Event()

event.wait(1)

print("ok")

while True:
  print("ok")
  event.wait(1)