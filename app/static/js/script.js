// static/js/script.js

document.addEventListener('DOMContentLoaded', function() {

    // --- Логика для главной страницы (index.html) ---
    const form = document.getElementById('process-form');
    const savedTemplateSelect = document.getElementById('saved_template');
    const newTemplateFields = document.getElementById('new-template-fields');

    // Показываем/скрываем поля для ручной настройки
    if (savedTemplateSelect) {
        savedTemplateSelect.addEventListener('change', function() {
            newTemplateFields.style.display = this.value ? 'none' : 'block';
        });
        // Проверяем состояние при загрузке страницы
        newTemplateFields.style.display = savedTemplateSelect.value ? 'none' : 'block';
    }

    // --- НОВАЯ ФУНКЦИЯ ОПРОСА (POLLING) ---
    function startPollingTaskStatus(taskId) {

        updateProgress('Задача в очереди...', 0);

        const intervalId = setInterval(() => {
            // Используем эндпоинт, который у вас уже есть
            fetch(`/api/task_status/${taskId}`)
                .then(response => {
                    if (response.status === 404) {
                        return { status: 'NOT_FOUND' };
                    }
                    if (response.status === 403) {
                        return { status: 'FORBIDDEN' };
                    }
                    if (!response.ok) {
                        throw new Error(`Ошибка сети: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    const statusBar = document.getElementById('progress-bar');

                    if (data.status === 'NOT_FOUND') {
                        updateProgress('Задача не найдена на сервере.', 100);
                        if(statusBar) statusBar.style.backgroundColor = 'var(--error-color)';
                        clearInterval(intervalId);
                        return;
                    }
                     if (data.status === 'FORBIDDEN') {
                        updateProgress('Ошибка: Доступ к задаче запрещен.', 100);
                        if(statusBar) statusBar.style.backgroundColor = 'var(--error-color)';
                        clearInterval(intervalId);
                        return;
                    }

                    // Обновляем UI
                    updateProgress(data.status, data.progress);

                    // --- ОБРАБОТКА ПРЕДУПРЕЖДЕНИЙ ---
                    if (data.warnings && data.warnings.length > 0) {
                        const warningContainer = document.getElementById('warning-container');
                        const warningList = document.getElementById('warning-list');

                        if (warningContainer && warningList) {
                            warningList.innerHTML = ''; // Очищаем старые

                            const maxWarningsToShow = 50;
                            data.warnings.slice(0, maxWarningsToShow).forEach(msg => {
                                const li = document.createElement('li');
                                li.textContent = msg;
                                warningList.appendChild(li);
                            });

                            if (data.warnings.length > maxWarningsToShow) {
                                 const li = document.createElement('li');
                                 li.style.fontWeight = 'bold';
                                 li.textContent = `... и еще ${data.warnings.length - maxWarningsToShow} замечаний.`;
                                 warningList.appendChild(li);
                            }

                            warningContainer.style.display = 'block';
                        }
                    }
                    // --- КОНЕЦ ОБРАБОТКИ ПРЕДУПРЕЖДЕНИЙ ---

                    // --- Проверка завершения ---
                    const isError = data.status && data.status.startsWith('Ошибка');
                    const isSuccess = data.result_ready === true;

                    if (isSuccess || isError) {
                        clearInterval(intervalId);

                        if (isSuccess) {
                            // Успех
                            const downloadLink = document.getElementById('download-link');
                            downloadLink.href = `/download/${taskId}`; // Используем task_id
                            downloadLink.style.display = 'inline-block';
                            updateProgress('Готово! Ваш файл можно скачать.', 100);

                        } else if (isError) {
                            // Ошибка
                            if(statusBar) statusBar.style.backgroundColor = 'var(--error-color)';
                        }
                    }
                })
                .catch(error => {
                    console.error('Ошибка опроса статуса:', error);
                    updateProgress(`Ошибка опроса: ${error.message}`, 100);
                    const statusBar = document.getElementById('progress-bar');
                    if(statusBar) statusBar.style.backgroundColor = 'var(--error-color)';
                    clearInterval(intervalId);
                });
        }, 2000); // Опрос каждые 2 секунды
    }

    // --- Общая функция обновления UI (без изменений) ---
    function updateProgress(status, progress) {
        const statusBar = document.getElementById('progress-bar');
        const statusText = document.getElementById('status-text');

        if (statusBar && statusText) {
            statusText.textContent = status || 'Обработка...';
            const progressVal = progress || 0;
            statusBar.style.width = `${progressVal}%`;
            statusBar.textContent = `${progressVal}%`;
        }
    }

    // Обработка отправки главной формы (ЗАПУСК ПАРСИНГА)
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(form);
            const errorContainer = document.getElementById('error-messages');
            const progressContainer = document.getElementById('progress-container');
            const downloadLink = document.getElementById('download-link');
            const warningContainer = document.getElementById('warning-container');
            const warningList = document.getElementById('warning-list');

            // Сбрасываем UI перед новым запуском
            errorContainer.style.display = 'none';
            progressContainer.style.display = 'block';
            downloadLink.style.display = 'none';
            if (warningContainer && warningList) {
                warningContainer.style.display = 'none';
                warningList.innerHTML = '';
            }
            const statusBar = document.getElementById('progress-bar');
            if (statusBar) {
                statusBar.style.width = `0%`;
                statusBar.textContent = `0%`;
                statusBar.style.backgroundColor = 'var(--success-color)';
            }
            updateProgress('Загрузка файлов на сервер...', 0);

            // Отправляем файлы на /process
            fetch(form.action, { method: 'POST', body: formData })
                .then(response => response.json())
                .then(data => {
                    if (data.error) { throw new Error(data.error); }
                    if (data.task_id) {
                        console.log('Задача запущена, ID:', data.task_id);
                        startPollingTaskStatus(data.task_id); // Запускаем опрос
                    } else {
                        throw new Error('Сервер не вернул ID задачи.');
                    }
                })
                .catch(error => {
                    progressContainer.style.display = 'none';
                    errorContainer.textContent = `Произошла ошибка: ${error.message}`;
                    errorContainer.style.display = 'block';
                });
        });
    }

    // --- Логика для страниц создания/редактирования шаблонов ---

    /**
     * Собирает имена листов из секции "Настройки листов источника" (Шаг 2)
     * и создает HTML-строку для выпадающего списка.
     * @param {string} selectName - Атрибут 'name' для нового <select>
     * @param {string} containerId - ID контейнера (div), в который добавляется правило.
     * @returns {string} - HTML-строка, содержащая <div class="rule-input-group">...</div>
     */
    function buildSheetSelectHtml(selectName, containerId) {
        const sheetSettingsContainer = document.getElementById('sheet-settings-container');
        if (!sheetSettingsContainer) return ''; // Безопасность

        // 1. Собираем все имена листов из Шага 2
        const sheetNameInputs = sheetSettingsContainer.querySelectorAll('input[name="setting_sheet_name"]');
        const sheetNames = Array.from(sheetNameInputs).map(input => input.value).filter(Boolean);

        // 2. Ищем последнее значение в текущей секции (для автозаполнения)
        const ruleContainer = document.getElementById(containerId);
        let lastSheetValue = '';
        if (ruleContainer) {
            const lastRuleRow = ruleContainer.querySelector('.rule-row:last-child');
            if (lastRuleRow) {
                // Ищем select с именем, начинающимся так же (source_sheet_...)
                const lastSelect = lastRuleRow.querySelector(`select[name^="${selectName.split('_')[0]}"]`);
                if (lastSelect) {
                    lastSheetValue = lastSelect.value;
                }
            }
        }

        // 3. Строим HTML для <select>
        let optionsHtml = '';
        if (sheetNames.length === 0) {
            optionsHtml = '<option value="">Сначала задайте листы в Шаге 2</option>';
        } else {
            sheetNames.forEach(name => {
                // Автовыбираем, если имя совпадает с последним
                const isSelected = (name === lastSheetValue) ? 'selected' : '';
                optionsHtml += `<option value="${name}" ${isSelected}>${name}</option>`;
            });
        }

        // 4. (Для edit_template.html) Проверяем, нет ли сохраненного значения,
        // которое удалили из Шага 2.
        // `templateSheetSettings` определяется в edit_template.html
        const existingSheetNames = window.templateSheetSettings || [];

        if (lastSheetValue && !sheetNames.includes(lastSheetValue) && existingSheetNames.includes(lastSheetValue)) {
             // Это значение пришло при загрузке страницы, но его уже нет в Шаге 2
             optionsHtml = `<option value="${lastSheetValue}" selected disabled>${lastSheetValue} (удален из Шага 2)</option>` + optionsHtml;
        }

        return `
            <div class="rule-input-group">
                <label>Из листа</label>
                <select name="${selectName}" required>${optionsHtml}</select>
            </div>
        `;
    }

    /**
     * Хелпер-функция для автозаполнения ТЕКСТОВЫХ полей (input)
     * @param {string} containerId - ID контейнера (div), в который добавляется правило.
     * @param {string} inputName - Атрибут 'name' для поиска
     * @param {string} defaultValue - Значение по умолчанию
     * @returns {string} - Значение для 'value'
     */
    function getAutofillValue(containerId, inputName, defaultValue = 'Лист1') {
        const container = document.getElementById(containerId);
        if (container) {
            const lastRuleRow = container.querySelector('.rule-row:last-child');
            if (lastRuleRow) {
                const lastInput = lastRuleRow.querySelector(`input[name="${inputName}"]`);
                if (lastInput) {
                    return lastInput.value;
                }
            }
        }
        return defaultValue;
    }


    // Кнопка для НАСТРОЕК ЛИСТОВ (Шаг 2)
    document.getElementById('add-sheet-setting')?.addEventListener('click', function() {
        const container = document.getElementById('sheet-settings-container');
        const ruleRow = document.createElement('div');
        ruleRow.className = 'rule-row';
        ruleRow.innerHTML = `
            <div class="rule-input-group">
                <label>Имя листа в источнике</label>
                <input type="text" name="setting_sheet_name" placeholder="Лист1" required>
            </div>
            <div class="rule-input-group">
                <label>Начальная ячейка заголовков</label>
                <input type="text" name="setting_start_cell" placeholder="A5" required>
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-rule-btn" style="align-self: center; margin-top: 1rem;">Удалить</button>`;
        container.appendChild(ruleRow);
    });

    // Кнопка для правил ЯЧЕЕК (Шаг 3)
    document.getElementById('add-cell-mapping')?.addEventListener('click', function() {
        const containerId = 'cell-mappings-container';
        const container = document.getElementById(containerId);
        const ruleRow = document.createElement('div');
        ruleRow.className = 'rule-row';

        const sheetSelectHtml = buildSheetSelectHtml('source_sheet_cell', containerId);

        ruleRow.innerHTML = `
            ${sheetSelectHtml}
            <div class="rule-input-group"><label>Из ячейки</label><input type="text" name="source_cell_cell" placeholder="A1" required></div>
            <div class="rule-arrow">→</div>
            <div class="rule-input-group"><label>В ячейку</label><input type="text" name="dest_cell_cell" placeholder="B5" required></div>

            <div class="rule-input-group rule-name-group">
                <label>Название (необяз.)</label><input type="text" name="cell_mapping_name" placeholder="Описание правила">
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-rule-btn" style="align-self: center; margin-top: 1rem;">Удалить</button>`;
        container.appendChild(ruleRow);
    });

    // Кнопка для ЗАПОЛНЕНИЯ ИЗ ЯЧЕЙКИ (Шаг 4)
    document.getElementById('add-source-fill-rule')?.addEventListener('click', function() {
        const containerId = 'source-cell-fill-rules-container';
        const container = document.getElementById(containerId);
        const ruleRow = document.createElement('div');
        ruleRow.className = 'rule-row';

        const sheetSelectHtml = buildSheetSelectHtml('source_sheet_fill', containerId);
        const lastTargetSheet = getAutofillValue(containerId, 'target_sheet_fill', 'Лист1');

        ruleRow.innerHTML = `
            ${sheetSelectHtml}
            <div class="rule-input-group"><label>Из ячейки источника</label><input type="text" name="source_cell_fill" placeholder="A2" required></div>
            <div class="rule-arrow">→</div>
            <div class="rule-input-group"><label>На лист шаблона</label><input type="text" name="target_sheet_fill" placeholder="Лист1" value="${lastTargetSheet}" required></div>
            <div class="rule-input-group"><label>В колонку шаблона</label><input type="text" name="target_col_fill" placeholder="C" required></div>

            <div class="rule-input-group rule-name-group">
                <label>Название (необяз.)</label><input type="text" name="source_cell_fill_rule_name" placeholder="Описание правила">
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-rule-btn" style="align-self: center; margin-top: 1rem;">Удалить</button>`;
        container.appendChild(ruleRow);
    });


    // Кнопка для правил КОЛОНОК (Шаг 5)
    document.getElementById('add-manual-rule')?.addEventListener('click', function() {
        const containerId = 'manual-rules-container';
        const container = document.getElementById(containerId);
        const ruleRow = document.createElement('div');
        ruleRow.className = 'rule-row';

        const sheetSelectHtml = buildSheetSelectHtml('source_sheet', containerId);

        ruleRow.innerHTML = `
            ${sheetSelectHtml}
            <div class="rule-input-group"><label>Из колонки</label><input type="text" name="source_col" placeholder="A" required></div>
            <div class="rule-arrow">→</div>
            <div class="rule-input-group"><label>В колонку</label><input type="text" name="template_col" placeholder="B" required></div>

            <div class="rule-input-group rule-name-group">
                <label>Название (необяз.)</label><input type="text" name="manual_rule_name" placeholder="Описание правила">
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-rule-btn" style="align-self: center; margin-top: 1rem;">Удалить</button>`;
        container.appendChild(ruleRow);
    });

    // Кнопка для СТАТИЧНЫХ ЗНАЧЕНИЙ (Шаг 6)
    document.getElementById('add-static-value-rule')?.addEventListener('click', function() {
        const containerId = 'static-value-rules-container';
        const container = document.getElementById(containerId);
        const ruleRow = document.createElement('div');
        ruleRow.className = 'rule-row';

        // Автозаполнение для target_sheet
        const lastTargetSheet = getAutofillValue(containerId, 'target_sheet_static', 'Лист1');

        ruleRow.innerHTML = `
            <div class="rule-input-group"><label>На лист шаблона</label><input type="text" name="target_sheet_static" placeholder="Лист1" value="${lastTargetSheet}" required></div>
            <div class="rule-input-group" style="flex-grow: 0.5;"><label>В колонку</label><input type="text" name="target_col_static" placeholder="D" required></div>
            <div class="rule-arrow">=</div>
            <div class="rule-input-group" style="flex-grow: 2;"><label>Вставить значение</label><input type="text" name="static_value" placeholder="Готово" required></div>

            <div class="rule-input-group rule-name-group">
                <label>Название (необяз.)</label><input type="text" name="static_value_rule_name" placeholder="Описание правила">
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-rule-btn" style="align-self: center; margin-top: 1rem;">Удалить</button>`;
        container.appendChild(ruleRow);
    });

    // Кнопка для правил ФОРМУЛ (Шаг 6)
    document.getElementById('add-formula-rule')?.addEventListener('click', function() {
        const containerId = 'formula-rules-container';
        const container = document.getElementById(containerId);
        const ruleRow = document.createElement('div');
        ruleRow.className = 'rule-row';

        const sheetSelectHtml = buildSheetSelectHtml('source_sheet_formula', containerId);
        const lastTargetSheet = getAutofillValue(containerId, 'target_sheet_formula', 'Лист1');

        ruleRow.innerHTML = `
            ${sheetSelectHtml}
            <div class="rule-arrow">→</div>
            <div class="rule-input-group"><label>На лист шаблона</label><input type="text" name="target_sheet_formula" placeholder="Лист1" value="${lastTargetSheet}" required></div>
            <div class="rule-input-group" style="flex-grow: 0.5;"><label>В колонку</label><input type="text" name="target_col_formula" placeholder="C" required></div>
            <div class="rule-arrow">=</div>
            <div class="rule-input-group" style="flex-grow: 2;"><label>Вычислить по формуле</label><input type="text" name="formula_string" placeholder="=A{row}*1.2" required></div>

            <div class="rule-input-group rule-name-group">
                <label>Название (необяз.)</label><input type="text" name="formula_rule_name" placeholder="Описание правила">
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-rule-btn" style="align-self: center; margin-top: 1rem;">Удалить</button>`;
        container.appendChild(ruleRow);
    });

    // Общая логика для УДАЛЕНИЯ правил из любого контейнера (без изменений)
    const allContainers = [
        document.getElementById('manual-rules-container'),
        document.getElementById('cell-mappings-container'),
        document.getElementById('formula-rules-container'),
        document.getElementById('static-value-rules-container'),
        document.getElementById('sheet-settings-container'),
        document.getElementById('source-cell-fill-rules-container')
    ];
    allContainers.forEach(container => {
        if (container) {
            container.addEventListener('click', function(e) {
                if (e.target?.classList.contains('remove-rule-btn')) {
                    e.target.closest('.rule-row').remove();
                }
            });
        }
    });

    // Логика для кнопок "Редактировать" на страницах словарей (без изменений)
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const canonical = this.dataset.canonical;
            const synonyms = this.dataset.synonyms;

            const form = this.closest('.container').querySelector('form');
            if(form) {
                form.querySelector('input[name*="canonical_"]').value = canonical;
                form.querySelector('input[name*="synonyms"], input[name*="find_words"]').value = synonyms;
                form.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    });

});