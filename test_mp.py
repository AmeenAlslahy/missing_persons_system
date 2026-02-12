import mediapipe as mp
try:
    print(f"MediaPipe version: {mp.__version__}")
except:
    print("Could not get version")

try:
    from mediapipe import solutions
    print("Success: from mediapipe import solutions")
    print(f"Face Detection: {solutions.face_detection}")
except ImportError as e:
    print(f"Failed: from mediapipe import solutions: {e}")

try:
    import mediapipe.python.solutions as solutions_pkg
    print("Success: import mediapipe.python.solutions")
except ImportError as e:
    print(f"Failed: import mediapipe.python.solutions: {e}")

print(f"Dir(mp): {dir(mp)}")
