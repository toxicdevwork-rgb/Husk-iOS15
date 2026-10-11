# Порт Husk на iOS 15.6.1: состояние

Цель: iPhone 12 mini, A14, iOS 15.6.1, Dopamine/TrollStore.
Основа: [Leviidev/Husk, 6b59e21](https://github.com/Leviidev/Husk/tree/6b59e21dbe6ac7013f237c149f995c231a05900b).
Локальная ветка: `codex/ios15-backport`.

**Сборка №8 успешно создала IPA и TIPA через GitHub Actions.**
[Результат](https://github.com/toxicdevwork-rgb/Husk-iOS15/actions/runs/38165267807)
· [Архив с пакетами](https://github.com/toxicdevwork-rgb/Husk-iOS15/actions/runs/38165267807/artifacts/11712386304).

В сборке исправлена упаковка Java/Android-ресурсов, добавлены 358 переводов,
проверка совместного использования JIT, настройка памяти и диагностика загрузки.
15 локальных проверок прошли; Java-рантайм собран в CI, комплектность проверяется
до выдачи IPA. Для TrollStore используйте файл `Husk-iOS15.tipa`.

На предыдущей сборке подтверждены открытие Husk и успешная проверка JIT на iPhone.
**Работа Discord и загрузка Android после исправлений требуют повторного теста на устройстве.**
Для Discord отключите автозапуск Android в настройках JIT и полностью перезапустите Husk.
Для Android выберите CPU и освободите не менее 3 ГБ. Если загрузка не продвигается,
откройте журнал кнопкой на экране запуска и сохраните все предлагаемые файлы журналов.

Форк хранит изменения в `husk-ios15.patch`; workflow применяет их к закреплённому
upstream commit. Исходники в корне GitHub — базовая версия, а не результат применения патча.

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
brew install meson ninja pkg-config xcodegen qemu e2fsprogs openjdk@17
python3 -m venv .build-python
source .build-python/bin/activate
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
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

`ci_build.sh` теперь собирает обязательные `android-system` и `java-runtime` из
закреплённого образа Lineage v12. SHA-256 проверяется до извлечения. JDK 17 и R8 8.5.35
создают `husk-framework.dex` из исходников. Проверка пакета отклоняет отсутствующие JAR,
JAR без `classes.dex`, библиотеки неверной архитектуры и отсутствующие шрифты/сертификаты.

Отдельная сборка интерфейса без этих ресурсов не считается полной IPA.

### Исправления после проверки на iPhone 12 mini

- Русский интерфейс по умолчанию; переключатель RU/EN в настройках (с перезапуском).
- QEMU и трансляция не запускаются в одном процессе одновременно: они использовали одну
  заранее выделенную область JIT. Для смены режима требуется полностью перезапустить Husk.
- Программная графика Android по умолчанию. GPU остаётся экспериментальной настройкой.
- На устройствах с 4 ГБ RAM и меньше используется кандидат 2 ГБ для файла памяти вместо
  попыток выделить 4–5 ГБ; до запуска проверяется свободное место (нужно минимум 3 ГБ).
- При учёте памяти резервируется фактический размер JIT 512 МБ. Ошибки выделения
  запоминаются отдельно для файловой и анонимной памяти.
- Экран загрузки показывает реальные этапы и прошедшее время, позволяет открыть/отправить
  журналы; без новых этапов появляется диагностическое сообщение.

Работа Discord и полная загрузка Android после этих изменений требуют повторной проверки
на устройстве. Устранение отсутствующих ресурсов само по себе не доказывает совместимость
всех Android API или библиотек React Native. Журналы пользователя в репозиторий не включены.

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


## Discord image compatibility follow-up

The device report reached the Android compatibility runtime and failed in
Fresco ImageRequestBuilder while creating a chat view. Husk's Uri.Builder
produced opaque `res:123` instead of hierarchical `res:/123`, so getPath()
returned null. The builder now inserts the required slash for a scheme.

BitmapFactory ignored inBitmap and Bitmap.reconfigure did nothing. The decoder
now returns the supplied mutable bitmap, keeps its allocation capacity stable,
updates its dimensions, copies decoded pixels, and releases temporary storage.
This addresses Fresco's identity checks and pool-accounting failures. Regression
tests run on the CI host; the native implementation is compiled for iOS.
Rendering and chat interactions still require a device retest.

The translation runtime has a separate long-session limitation: Runtime.nativeGc
is a no-op and tl_jni_unref intentionally retains objects while the DVM is active.
Changing guest VM RAM does not implement Java garbage collection. Do not describe
this build as memory-bounded or fully compatible with Discord.

The wrapper repository also has a separate 1024 MiB guest experiment. It enables
Android's low-RAM configuration, reduces ART heaps, preserves the core services
and Husk shell bridge, and checks a real cold boot before exporting the image.
It does not replace the app's guest automatically or claim that all of Husk fits
in 1 GiB. The iOS process also needs QEMU, translated code and rendering memory.

Reference contracts: [AOSP Uri.Builder](https://android.googlesource.com/platform/frameworks/base/+/a69950c/core/java/android/net/Uri.java) and [Fresco image decoder](https://github.com/facebook/fresco/tree/main/imagepipeline/src/main/java/com/facebook/imagepipeline/platform).
