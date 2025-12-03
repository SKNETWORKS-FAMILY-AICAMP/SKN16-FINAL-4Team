이 파일에는 EC2용 IAM 역할을 생성하고 S3 정책을 연결한 다음 인스턴스 프로필을 생성하여 EC2 인스턴스에 연결하는 정확한 AWS CLI 명령어들이 포함되어 있습니다.

사전 요구사항
- IAM 역할 생성(CreateRole), 정책 생성(CreatePolicy), 역할에 정책 연결(AttachRolePolicy) 권한이 있는 AWS CLI 사용자가 필요합니다.
- 계정 ID: <`ACCOUNT-ID`>
- 버킷 이름: <`S3-BUCKET`>

절차 (명령어 복사 & 붙여넣기)

1) IAM 역할 생성 (EC2 신뢰 정책)

```bash
aws iam create-role \
  --role-name PersonalColorAnalyzeServerRole \
  --assume-role-policy-document file://trust-ec2.json
```

2) S3 정책 생성 (이미 생성되어 있지 않은 경우)

```bash
aws iam create-policy --policy-name PersonalColorAnalyzeS3Policy --policy-document file://policy-s3-server.json
```

명령을 실행하면 출력에 `Policy.Arn`이 표시됩니다. 이를 저장해 두거나 아래 형식의 ARN을 계정에 맞게 사용하세요:
`arn:aws:iam::<ACCOUNT-ID>:policy/PersonalColorAnalyzeS3Policy`

3) 역할에 정책 연결

```bash
aws iam attach-role-policy --role-name PersonalColorAnalyzeServerRole --policy-arn arn:aws:iam::<ACCOUNT-ID>:policy/PersonalColorAnalyzeS3Policy
```

4) 인스턴스 프로필 생성 및 역할 추가 (EC2가 역할을 맡을 수 있도록)

```bash
aws iam create-instance-profile --instance-profile-name PersonalColorAnalyzeInstanceProfile
aws iam add-role-to-instance-profile --instance-profile-name PersonalColorAnalyzeInstanceProfile --role-name PersonalColorAnalyzeServerRole
```

5) 기존 EC2 인스턴스에 인스턴스 프로필 연결
- `<INSTANCE-ID>`를 실제 EC2 인스턴스 ID로 교체하세요.

```bash
aws ec2 associate-iam-instance-profile --instance-id <INSTANCE-ID> --iam-instance-profile Name=PersonalColorAnalyzeInstanceProfile
```

주의사항
- 위 역할은 `<S3-BUCKET>/uploads/*` 경로에 대해 `s3:PutObject` 및 `s3:GetObject` 권한만 부여합니다.
- EC2 인스턴스와 서버 코드가 동일한 AWS 계정(<`ACCOUNT-ID`>)에서 실행되고 있는지 확인하세요.
- 새 EC2 인스턴스를 생성하면서 프로필을 지정하려면 `aws ec2 run-instances` 실행 시 `--iam-instance-profile Name=PersonalColorAnalyzeInstanceProfile` 옵션을 사용하면 됩니다.

테스트
- 프로필이 적용된 EC2 인스턴스에서(프로필 적용 후) boto3를 사용하는 서버를 실행하여 S3 접근을 확인하거나 AWS CLI로 테스트할 수 있습니다:
```bash
# 객체 목록 (객체가 없으면 실패할 수 있음)
aws s3 ls s3://<S3-BUCKET>/uploads/ --recursive
```

정리(삭제)
- 정책-역할 연결을 제거하려면:
```bash
aws iam detach-role-policy --role-name PersonalColorAnalyzeServerRole --policy-arn arn:aws:iam::<ACCOUNT-ID>:policy/PersonalColorAnalyzeS3Policy
```
- 역할을 인스턴스 프로필에서 제거하고 리소스를 삭제하려면 IAM/EC2 문서를 참고하세요.
