#!/bin/zsh

# common.shをsource
source "$(dirname "$0")/common.sh"

# Geminiのsettings.jsonがシンボリックリンクになっているかチェック
# （Geminiがsettings.jsonを更新するとsettings.json.origに移動されてしまう）
check_gemini_symlink() {
    local GEMINI_SETTINGS="${HOME}/.gemini/settings.json"
    local GEMINI_SOURCE="${SET}ai/gemini/settings.json"

    echo "Checking Gemini settings.json symlink..."

    if [ -e "${GEMINI_SETTINGS}" ]; then
        if [ ! -L "${GEMINI_SETTINGS}" ]; then
            echo "⚠️  Gemini settings.json is not a symlink."

            # 既存ファイルがある場合、内容を比較
            if [ -f "${GEMINI_SETTINGS}" ]; then
                echo "  Found regular file. Checking differences..."

                # 差分がある場合は表示
                if ! diff -q "${GEMINI_SOURCE}" "${GEMINI_SETTINGS}" >/dev/null 2>&1; then
                    echo "  📝 Differences found between source and current file:"
                    diff "${GEMINI_SOURCE}" "${GEMINI_SETTINGS}" || true

                    # 現在のファイル（Geminiの変更）をソースファイルに反映
                    echo "  📋 Copying Gemini changes to source file..."
                    cp "${GEMINI_SETTINGS}" "${GEMINI_SOURCE}"
                    echo "  ✅ Updated source with Gemini changes"
                fi

                # どちらの場合でも最終的にシンボリックリンクに変換
                echo "  🔗 Converting to symlink..."
                make_symlink "${GEMINI_SOURCE}" "${GEMINI_SETTINGS}"
                echo "  ✅ Converted to symlink"
            fi
        else
            # シンボリックリンクが正しいターゲットを指しているかチェック
            local CURRENT_TARGET=$(readlink "${GEMINI_SETTINGS}")
            if [ "${CURRENT_TARGET}" != "${GEMINI_SOURCE}" ]; then
                echo "⚠️  Symlink points to wrong target:"
                echo "  Current: ${CURRENT_TARGET}"
                echo "  Expected: ${GEMINI_SOURCE}"

                # 間違ったシンボリックリンクを削除して、正しいシンボリックリンクを作成
                make_symlink "${GEMINI_SOURCE}" "${GEMINI_SETTINGS}"
                echo "✅ Fixed symlink target"
            else
                echo "✅ Gemini settings.json symlink is correctly configured"
            fi
        fi
    else
        echo "⚠️  Gemini settings.json(${GEMINI_SETTINGS}) does not exist."
        echo "  Creating directory and symlink..."
        make_symlink "${GEMINI_SOURCE}" "${GEMINI_SETTINGS}"
        echo "✅ Created Gemini settings.json symlink"
    fi
}

# 関数を実行
check_gemini_symlink