from deep_translator import GoogleTranslator


def main() -> None:
    text = "Amazon S3是一個對象存儲服務，用於存儲和檢索任何數量的數據。它不是數據庫服務，因此此選項錯誤。"
    result = GoogleTranslator(source="zh-TW", target="en").translate(text)
    print(result)


if __name__ == "__main__":
    main()
