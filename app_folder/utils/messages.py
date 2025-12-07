from ..constants import INFO_MESSAGES, WORNING_MESSAGES, ERROR_MESSAGES
from django.utils import timezone
def info_messages(*args):
    dm = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    if args and len(args) == 2:
        if args[0] == "info_001":
            # [info_001]:【処理内容】-- 開始
            message = INFO_MESSAGES[args[0]].format(action=args[1])
        elif args[0] == "info_002":
            # [info_002]:【処理内容】-- 終了
            message = INFO_MESSAGES[args[0]].format(action=args[1])
        elif args[0] == "info_003":
            # [info_003]:【処理内容】を正常に終了しました。
            message = INFO_MESSAGES[args[0]].format(action=args[1])
        else:
            message = f"エラーメッセージを使用する際は、適切な引数をセットしてください。(args[0]:{args[0]})"
    else:
        if len(args) > 0:
            message = f"指定のエラータイプ（{args[0]}）がありません。"
        else:
            message = "エラーメッセージを使用する際は、適切な引数をセットしてください。"

    return message

def worn_messages(*args):
    dm = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    if args and len(args) == 1:
        if args[0] == "worn_001":
            # [worn_001]:オッズ情報の取得ができませんしオッズ情報が取得できませんでした。再度、オッズ情報の取得を試みます。
            message = WORNING_MESSAGES[args[0]]
        else:
            message = f"エラーメッセージを使用する際は、適切な引数をセットしてください。(args[0]:{args[0]})"
    else:
        if len(args) > 0:
            message = f"指定のエラータイプ（{args[0]}）がありません。"
        else:
            message = "エラーメッセージを使用する際は、適切な引数をセットしてください。"

    return message

def err_messages(*args):
    dm = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    if args and len(args) == 6:
        # 【yyyy-MM-dd hh:mm:ss】-- ファイル名 > クラス名 > 関数名 > 行数 -- エラー内容：エラー。
        message = ERROR_MESSAGES[args[0]].format(time=dm, file=args[1], classnm=args[2], func=args[3], line=args[4], error=args[5])
    elif args and len(args) == 2:
        if args[0] == "timeout_error":
            # 【yyyy-MM-dd hh:mm:ss】-- URL -- 次の処理へ進みます。
            message = ERROR_MESSAGES[args[0]].format(time=dm, url=args[1])
        elif args[0] == "error_001":
            #  [error_001]:アクションに失敗しました。エラーログを確認してください。
            message = ERROR_MESSAGES[args[0]].format(action=args[1])
        else:
            message = f"エラーメッセージを使用する際は、適切な引数をセットしてください。(args[0]:{args[0]})"
    elif args and len(args) == 1:
        # [error_000]:予期しないエラーが発生しました。エラーログを確認してください。
        message = ERROR_MESSAGES[args[0]]
    else:
        if len(args) > 0:
            message = f"指定のエラータイプ（{args[0]}）がありません。"
        else:
            message = "エラーメッセージを使用する際は、適切な引数をセットしてください。"

    return message