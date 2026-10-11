# Порт Husk на iOS 15.6.1: состояние

Цель: iPhone 12 mini, A14, iOS 15.6.1, Dopamine/TrollStore.
Основа: [Leviidev/Husk, 6b59e21](https://github.com/Leviidev/Husk/tree/6b59e21dbe6ac7013f237c149f995c231a05900b).
Локальная ветка: `codex/ios15-backport`.

**IPA и TIPA собраны через GitHub Actions; работа на iPhone ещё не проверена.**
[Сборка №4](https://github.com/toxicdevwork-rgb/Husk-iOS15/actions/runs/38151341187)
скомпилировала и упаковала приложение с Xcode 26.6 на macOS Intel runner.
QEMU, ANGLE, libepoxy, virglrenderer, MoltenVK и Rust-библиотека собраны из исходников.
Проверка всех пяти Mach-O в пакете прошла: arm64, iOS device, minOS <= 15.6.1.
[Архив IPA/TIPA](https://github.com/toxicdevwork-rgb/Husk-iOS15/actions/runs/38151341187/artifacts/11706817512)
также содержит логи, патч и SHA256SUMS.txt. Внутри архива пакеты лежат в
`Users/runner/work/Husk-iOS15/Husk-iOS15/husk/build/`.
На доступном Windows-хосте нет подключённого iPhone: установка, JIT и запуск
Android-приложений требуют отдельной проверки на устройстве.

## Что показала проверка исходников

- В текущем upstream нет `scripts/build_dependencies.sh` и workflow `build-ipa.yml`.
  Входная точка — `scripts/ci_build.sh`, QEMU собирает `scripts/build_ios.sh`.
- QEMU, ANGLE и Rust-библиотека pairing уже имели minOS 15.5. В этой ветке первые
  три скрипта по умолчанию используют 15.6. MoltenVK v1.4.2 в своём
  [проекте](https://github.com/KhronosGroup/MoltenVK/blob/v1.4.2/MoltenVK/MoltenVK.xcodeproj/project.pbxproj)
  задаёт minOS 15.0; понижать его не требуется. Реальный результат проверяется по Mach-O.
- В `src/ios-jit/husk-ios-jit.c` уже есть самостоятельное выделение исполняемой памяти
  и тест исполнения для систем до iOS 26: MAP_JIT и отдельный путь для debugged/jailbroken
  процесса. APRR и разделение RW/RX сохранены. Их работоспособность на A14 надо проверить
  на устройстве; замена на один `mprotect` сама по себе не выдаёт разрешение на JIT.
- [StikDebug](https://github.com/StikDebug/StikDebug) требует iOS 17.4+.
  Новый JavaScript не сделает его приложением для iOS 15. Скрипт `universal-ios15.js`
  не добавлялся. `get-task-allow` не заменяет предоставление JIT системой.
- ANGLE предоставляет EGL/OpenGL ES. MoltenVK предоставляет Vulkan поверх Metal,
  поэтому он не заменяет ANGLE для GLES-приложений и virglrenderer.
- У поставляемого `libFilePickerFix.dylib` arm64/minOS 15.0. У StikJIT.framework
  minOS 17.4; helper-расширение имеет target 26.0, widget — 16.1.

## Изменения

1. XcodeGen target 15.6; NavigationBackport 0.11.5 закреплён по commit SHA.
   Сохраняются массивы путей, переходы из уведомлений приложения и вложенные страницы.
   MIT-лицензия зависимости включена в ресурсы приложения.
2. `LabeledContent` и отправка файлов через `ShareLink` заменены совместимыми компонентами.
   Современные sheet/scroll/gesture API и анимации имеют проверки доступности.
   На iOS 15 используются обычные sheets и spring-анимации; скрытие home indicator
   и отсрочка системных жестов через эти SwiftUI-модификаторы там не применяются.
   Поворот экрана использует `attemptRotationToDeviceOrientation`; принудительный
   поворот и возвращение из игры требуют отдельного теста на телефоне.
3. Из target graph исключены StikJIT/helper и Live Activity widget; ActivityKit-код
   приложения отключён условием `HUSK_IOS15`. Автоматический JIT предпочитает Dopamine,
   затем доступный StikDebug на новых системах, иначе предлагает TrollStore.
4. ANGLE закреплён на WebKit `132c1a571cbe2549aff28a963c0c2502d50ebb92`.
   Эта ревизия успешно собрана с target 15.6 на GitHub runner (Xcode 26.6).
   Работа графики на iPhone ещё не проверена.
5. Упаковка требует генерации проекта и проверки каждого Mach-O в `.app`: generic arm64,
   iOS device platform, minOS <= 15.6.1, отсутствие новых расширений и известных
   недоступных strong-linked frameworks. Проверка не доказывает доступность всех
   импортируемых символов и не заменяет запуск.

## Сборка через GitHub Actions

Личный Mac не нужен: workflow использует macOS runner GitHub. В форке хранится
воспроизводимый патч `husk-ios15.patch`, который применяется к закреплённому
upstream-коммиту в отдельном checkout. Ниже также приведены команды для Mac.

Нужен современный Xcode с SDK, содержащим используемые upstream API iOS 26;
Xcode 13 и SDK iOS 15 не подходят. Deployment target и версия SDK — разные параметры.
Использовать чистый checkout без старых `build/`, `third_party/` и DerivedData:
скрипты upstream пропускают уже собранные зависимости по наличию файлов/stamps.

```sh
brew install meson ninja pkg-config xcodegen qemu
python3 -m venv .build-python
source .build-python/bin/activate
python -m pip install 'PyYAML==6.0.3' 'Mako==1.3.10'
rustup target add aarch64-apple-ios
python3 -m unittest discover -s tests -p 'test_ios15_*.py' -v
SDKMINVER=15.6 DD=/tmp/husk_ios15 ./scripts/ci_build.sh "$PWD/build/Husk-iOS15.ipa"
```

Либо вручную запустить `.github/workflows/build-ios15.yml` после публикации ветки
в собственном GitHub-репозитории. Workflow сохраняет IPA/TIPA и логи даже при ошибке.
Опубликованный workflow кэширует собственные зависимости отдельно по архитектуре
runner. При изменении target/версий зависимостей надо изменить версию ключа кэша.
Подпись ad hoc и различие IPA/TIPA
унаследованы от upstream; entitlements не удалялись только из-за возраста iOS.

`ci_build.sh` upstream не создаёт опциональные ресурсы `android-system` и `java-runtime`:
для приложений, которым нужны эти ресурсы, требуются соответствующие build-скрипты.
Это ограничение не устранено данным портом.

## Что проверено и что осталось

Локально прошли 9 тестов проверки пакета, разбор YAML/plist, синтаксис изменённых
shell-скриптов и `git diff --check`. Отдельно прочитаны заголовки двух поставляемых
Mach-O. SwiftUI и ARM64-код здесь не выполнялись.

Компиляция Swift/Objective-C и линковка успешно выполнены на GitHub.
Следующий обязательный шаг — проверка на iPhone:
первый запуск и навигация Home/Library/Files/JIT, назад/вперёд и программный переход,
импорт APK, экспорт отчёта, поворот игры, JIT self-test с фактическим исполнением кода,
запуск одного ARM64 GLES-приложения, Vulkan-приложения и отдельно QEMU-гостя.
Записать логи JIT, dyld, Metal и jetsam. До этого совместимость не подтверждена.
