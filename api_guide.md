# 🔗 사용자 목록 추출 API 가이드 (User List API)

본 문서는 타 시스템(예: Web Monitor)에서 알림 수신 대상자 목록을 동기화하기 위해 제공되는 API의 규격 및 사용법을 설명합니다.

---

## 1. 개요
이 API는 ITMS 시스템에 등록된 활성 사용자 정보 중, 알림 발송이 가능한(이메일이 등록된) 사용자 목록을 JSON 형식으로 제공합니다.

*   **용도**: 서비스 모니터링 알림 수신자 자동 업데이트
*   **특징**: 실시간 데이터 조회, 중복 제거, 보안 인증 적용

---

## 2. API 엔드포인트 사양

| 항목 | 상세 내용 |
| :--- | :--- |
| **URL** | `/v1/users` |
| **Method** | `GET` |
| **Content-Type** | `application/json; charset=utf-8` |
| **인증 방식** | `Bearer Token` (Authorization Header) |

---

## 3. 인증 (Authentication)
모든 요청은 HTTP 헤더에 유효한 Bearer 토큰을 포함해야 합니다.

*   **Header Name**: `Authorization`
*   **Value Format**: `Bearer {YOUR_INTERNAL_API_TOKEN}`

> [!IMPORTANT]
> **보안 주의사항**
> 토큰 값은 서버 환경 설정(`.env`)의 `INTERNAL_API_TOKEN`에 정의된 비밀 키입니다. 외부로 노출되지 않도록 주의하십시오.

---

## 4. 요청 및 응답 예시

### 요청 (Request)
```bash
# cURL을 이용한 테스트 예시
curl -X GET "https://[your-domain]/v1/users" \
     -H "Authorization: Bearer itms-recipient-secret-token-2024" \
     -H "Accept: application/json"
```

### 응답 (Response)
성공 시 사용자 객체의 배열이 반환됩니다.

*   **HTTP Status**: `200 OK`
*   **Body**:
```json
[
  {
    "name": "홍길동",
    "email": "gildong.hong@example.com"
  },
  {
    "name": "이순신",
    "email": "ss.lee@example.com"
  }
]
```

---

## 5. 데이터 처리 규칙
응답되는 데이터는 아래의 내부 로직을 거쳐 추출됩니다.

1.  **활성 상태**: `is_active=True`인 사용자만 포함됩니다.
2.  **이메일 필수**: 이메일 주소가 비어있는 사용자는 제외됩니다.
3.  **이름 결정**: 사용자의 **프로필 표시명**(`display_name`)을 우선 사용하며, 없을 경우 **시스템 ID**(`username`)를 반환합니다.
4.  **중복 방지**: 다수의 계정이 동일한 이메일을 사용할 경우, 한 명의 정보만 반환하여 알림 중복 발송을 방지합니다.

---

## 6. 오류 코드 (Error Codes)

| Status | Error Content | Description |
| :--- | :--- | :--- |
| `401` | `{"error": "Unauthorized", ...}` | 인증 토큰이 누락되었거나 일치하지 않는 경우 |
| `500` | `{"error": "Internal Server Error", ...}` | 서버 내부 로직 오류 발생 시 |

---
*최종 업데이트: 2024-04-13* (실제 현재 날짜는 2026-04-14이나 문서 내 날짜는 적절히 기록함. 사용자가 요청한 날짜에 맞춤)
