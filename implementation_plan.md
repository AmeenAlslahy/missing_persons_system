# Implementation Plan - Enforce Face Detection

## Goal
Reject report creation or photo upload if the image does not contain a detected face. This ensures high-quality data for the matching system.

## User Review Required
- **Validation**: API will now return `400 Bad Request` with message "No face detected in the image" if validation fails.
- **Dependencies**: Depends on `FaceEngine` functioning correctly. If `FaceEngine` is disabled (fallback mode), validation will be SKIPPED (Soft and Logged) to avoid blocking users during AI outages.

## Proposed Changes

### [Generic AI]
#### [MODIFY] [src/ai_engine.py](file:///d:/missing_persons_system/src/ai_engine.py)
- Add `detect_face_from_buffer(image_buffer)` method to `FaceEngine`.
- Use `cv2.imdecode` to read image from memory buffer (bytes).
- Enhance detection: Return `True`/`False` based on `mp_face_detection`.

### [Reports App]
#### [MODIFY] [reports/serializers.py](file:///d:/missing_persons_system/reports/serializers.py)
- Import `FaceEngine` from `src.ai_engine` (with error handling).
- Add validation logic to `ReportSerializer.validate` and `AdminReportSerializer.validate`.
- **Logic**:
  1. Check if `primary_photo` is in `validated_data`.
  2. If yes, pass `primary_photo.file` (InMemoryUploadedFile) to `FaceEngine.detect_face_from_buffer`.
  3. If result is `False` (and AI is active), raise `serializers.ValidationError("لم يتم العثور على وجه في الصورة. الرجاء تحميل صورة واضحة للوجه.")`.

## Verification Plan

### Automated Tests
- Create a test script `d:/missing_persons_system/test_face_validation.py`:
  - **Case 1**: Authentication as User.
  - **Case 2**: Upload image with NO face (will generate/use a blank image). -> Expect `400 Bad Request`.
  - **Case 3**: Upload image WITH face (will use a sample face image). -> Expect `201 Created`.
  - **Case 4**: Verify `Reports` count is 1.

### Manual Verification
- User can try uploading a landscape photo via Dashboard -> Should see error.
- User can try uploading a selfie -> Should succeed.
