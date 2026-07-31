import csv


class ExportService:
    @staticmethod
    def export_history_to_csv(filepath: str, history: list):
        if not history:
            raise ValueError("保存する履歴がありません")

        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "日時",
                    "URL",
                    "使用モデル",
                    "状態",
                    "パターン",
                    "タイトルタグ",
                    "文字数",
                    "メタディスクリプション",
                    "文字数",
                ]
            )

            for entry in history:
                title = entry.get("title_tag", "")
                desc = entry.get("description", "")
                writer.writerow(
                    [
                        entry.get("timestamp", ""),
                        entry.get("url", ""),
                        entry.get("model", ""),
                        entry.get("status", ""),
                        entry.get("pattern", ""),
                        title,
                        len(title),
                        desc,
                        len(desc),
                    ]
                )
