from dataclasses import dataclass
from enum import StrEnum


class BulkItemStatus(StrEnum):
    PENDING = "待機"
    FETCHING = "取得中"
    GENERATING = "生成中"
    SUCCESS = "成功"
    FAILED = "失敗"
    NOT_RUN = "未実行"
    CANCELLED = "キャンセル"


@dataclass(slots=True)
class BulkItemState:
    url: str
    status: BulkItemStatus = BulkItemStatus.PENDING
    message: str = ""

    def update(self, status: BulkItemStatus, message: str = "") -> None:
        self.status = status
        self.message = message
