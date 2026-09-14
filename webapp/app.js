let currentController = null;
document.addEventListener("DOMContentLoaded", () => {
    // Инициализация Telegram Web App
    const tg = window.Telegram.WebApp;
    tg.expand(); 
    setTimeout(() => {
        scrollToActiveDate(false);
    }, 50);
    tg.ready();
    
    // Устанавливаем цвет шапки Telegram в цвет нашего фона
    tg.setHeaderColor('bg_color');

    // Состояние приложения
    let state = {
        currentDate: '0', // '0' - сегодня, '-1' - вчера, '1' - завтра
        currentLeague: 'ALL' // 'ALL', 'KHL', 'NHL'
    };

    // --- Настройка профиля ---
    const userNameEl = document.getElementById('user-name');
    if (tg.initDataUnsafe?.user) {
        userNameEl.textContent = tg.initDataUnsafe.user.first_name;
    }

    // --- Навигация (Bottom Nav) ---
    const navButtons = document.querySelectorAll('.nav-btn');
    const pages = document.querySelectorAll('.page');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Переключаем активную кнопку
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Переключаем страницу
            const targetId = btn.getAttribute('data-target');
            pages.forEach(p => p.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');
        });
    });

    // --- Фильтры и Календарь ---
    // --- Система кэширования ---
    const matchCache = new Map(); // Кэш живет, пока открыт Web App

    // --- Вспомогательные функции (Безопасные для часовых поясов!) ---
    function getFormattedDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function addDays(date, days) {
        const result = new Date(date);
        result.setDate(result.getDate() + days);
        return result;
    }

    const actualToday = new Date();
    let currentDateObj = new Date();

    // Глобальные переменные для краев нашей ленты дат
    let leftmostDateObj;
    let rightmostDateObj;

    const monthNames = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
    const dayNames = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];

    // --- Фабрика DOM-элементов для даты ---
    function createDateNode(d) {
        const dateStr = getFormattedDate(d);
        const todayStr = getFormattedDate(actualToday);

        const btn = document.createElement('div');
        btn.className = 'date-item';
        btn.dataset.date = dateStr;

        if (dateStr === todayStr) {
            btn.classList.add('is-today');
        }

        const dayName = (dateStr === todayStr) ? "Сегодня" : dayNames[d.getDay()];
        const monthName = monthNames[d.getMonth()];

        btn.innerHTML = `
            <span class="day-name">${dayName}</span>
            <span class="day-num">${d.getDate()}</span>
            <span class="month-name">${monthName}</span>
        `;

        btn.addEventListener('click', () => {
            updateSelectedDate(dateStr);
        });

        return btn;
    }

    // --- Первичная инициализация ленты ---
    function initDateStrip(centerDate) {
        const strip = document.getElementById('date-strip');
        strip.innerHTML = '';
        
        // Рисуем по 15 дней в обе стороны от выбранной даты
        leftmostDateObj = addDays(centerDate, -15);
        rightmostDateObj = addDays(centerDate, 15);

        for (let i = -15; i <= 15; i++) {
            strip.appendChild(createDateNode(addDays(centerDate, i)));
        }
    }

    // --- БЕСКОНЕЧНЫЙ СКРОЛЛ ПОЛОСКИ ДАТ ---
    const stripElement = document.getElementById('date-strip');
    stripElement.addEventListener('scroll', () => {
        // Если докрутили почти до правого края (осталось меньше 100px)
        if (stripElement.scrollWidth - stripElement.scrollLeft - stripElement.clientWidth < 100) {
            // Подгружаем еще 10 дней вправо
            for (let i = 1; i <= 10; i++) {
                rightmostDateObj = addDays(rightmostDateObj, 1);
                stripElement.appendChild(createDateNode(rightmostDateObj));
            }
        }
        
        // Если докрутили почти до левого края (осталось меньше 100px)
        if (stripElement.scrollLeft < 100) {
            // Запоминаем текущие параметры скролла
            const oldScrollWidth = stripElement.scrollWidth;
            const oldScrollLeft = stripElement.scrollLeft;
            
            // Подгружаем еще 10 дней влево
            for (let i = 1; i <= 10; i++) {
                leftmostDateObj = addDays(leftmostDateObj, -1);
                stripElement.prepend(createDateNode(leftmostDateObj));
            }
            
            // Компенсируем сдвиг, чтобы визуально лента не прыгнула
            const newScrollWidth = stripElement.scrollWidth;
            stripElement.scrollLeft = oldScrollLeft + (newScrollWidth - oldScrollWidth);
        }
    });

    // --- Плавное переключение и центровка ---
    function updateSelectedDate(dateStr) {
        currentDateObj = new Date(dateStr);
        let activeBtn = document.querySelector(`.date-item[data-date="${dateStr}"]`);
        
        // Если дату выбрали через календарь и её вообще нет в нашем DOM — перерисовываем
        if (!activeBtn) {
            initDateStrip(currentDateObj);
            activeBtn = document.querySelector(`.date-item[data-date="${dateStr}"]`);
        }

        document.querySelectorAll('.date-item').forEach(el => el.classList.remove('active'));
        activeBtn.classList.add('active');
        
        // Прокручиваем полоску плавно к выбранной дате
        const scrollPosition = activeBtn.offsetLeft - (stripElement.clientWidth / 2) + (activeBtn.clientWidth / 2);
        stripElement.scrollTo({
            left: scrollPosition,
            behavior: 'smooth'
        });

        // Загружаем матчи (эту функцию не трогаем, она у тебя уже есть)
        loadMatches(dateStr, state.currentLeague);
    }

    // --- Управление кнопками и календарем ---
    document.getElementById('prev-day-btn').addEventListener('click', () => {
        updateSelectedDate(getFormattedDate(addDays(currentDateObj, -1)));
    });

    document.getElementById('next-day-btn').addEventListener('click', () => {
        updateSelectedDate(getFormattedDate(addDays(currentDateObj, 1)));
    });

    // Работа системного календаря
    const datePicker = document.getElementById('native-date-picker');
    const calendarBtn = document.getElementById('calendar-trigger-btn');

    calendarBtn.addEventListener('click', () => {
        try { datePicker.showPicker(); } 
        catch (e) { datePicker.focus(); datePicker.click(); }
    });

    datePicker.addEventListener('change', (e) => {
        if (e.target.value) {
            updateSelectedDate(e.target.value);
            e.target.value = ''; 
        }
    });

    // --- Запуск приложения ---
    initDateStrip(actualToday);
    updateSelectedDate(getFormattedDate(actualToday));

    function scrollToActiveDate(smooth = false) {
        const container = document.querySelector('.dates-container'); // селектор ленты с датами
        const activeItem = container?.querySelector('.date-item.active'); // селектор активной даты

        if (!container || !activeItem) return;

    // Вычисляем позицию, чтобы элемент встал строго по центру контейнера
        const containerWidth = container.offsetWidth;
        const itemWidth = activeItem.offsetWidth;
        const itemLeft = activeItem.offsetLeft;

        const targetScrollLeft = itemLeft - (containerWidth / 2) + (itemWidth / 2);

        container.scrollTo({
            left: targetScrollLeft,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }

    async function fetchHockeyMatches(dateStr, leagueStr) {
        const cacheKey = `${dateStr}_${leagueStr}`;
        const url = `https://api.khhljkmnbh.ru:8443/api/matches?date=${dateStr}&league=${leagueStr}`;
        const url1 = `http://193.93.252.110/api/matches?date=${dateStr}&league=${leagueStr}`;
        // Если данные есть в кэше, отдаем их сразу!
        if (matchCache.has(cacheKey)) {
            return matchCache.get(cacheKey);
        }

        try {
	    const response = await fetch(url, { cache: 'no-store' });
            if (!response.ok) throw new Error("HTTP error");
            const data = await response.json();
            
            if (data.status === "success") {
                // Сохраняем в кэш
                matchCache.set(cacheKey, data.matches);
                return data.matches;
            }
            return [];
        } catch (error) {
	    console.log(error);
	    return [];
	}
    }

    // --- Слежение за скроллом (Intersection Observer) ---
    // Этот код обновляет полосу дат, если пользователь скроллит ленту с разными днями
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            // Если блок с матчами определенной даты пересек середину экрана
            if (entry.isIntersecting) {
                const visibleDate = entry.target.dataset.dateGroup;
                const activeBtn = document.querySelector(`.date-item.active`);
                
                // Если видимая дата не совпадает с активной кнопкой наверху
                if (activeBtn && activeBtn.dataset.date !== visibleDate) {
                    // Если меняем дату прокруткой ленты вниз, просто сдвигаем полоску без загрузки новых матчей
                    currentDateObj = new Date(visibleDate);
                    
                    // Переключаем активную кнопку в полоске дат
                    document.querySelectorAll('.date-item').forEach(el => el.classList.remove('active'));
                    const newActive = document.querySelector(`.date-item[data-date="${visibleDate}"]`);
                    if (newActive) {
                        newActive.classList.add('active');
                        const strip = document.getElementById('date-strip');
                        strip.scrollTo({
                            left: newActive.offsetLeft - (strip.clientWidth / 2) + (newActive.clientWidth / 2),
                            behavior: 'smooth'
                        });
                    }
                    
                    window.Telegram.WebApp.HapticFeedback.selectionChanged();
                }
            }
        });
    }, { 
        rootMargin: "-50% 0px -50% 0px" // Срабатывает, когда элемент ровно в центре экрана
    });

    // --- Обновленный рендер матчей ---
    async function loadMatches(dateStr, leagueStr, append = false) {
        const container = document.getElementById('matches-container');
        
        if (!append) {
            container.innerHTML = '<div class="loading">Загрузка...</div>';
        } else {
            container.insertAdjacentHTML('beforeend', '<div id="temp-load" class="loading">Подгружаем...</div>');
        }

        const matches = await fetchHockeyMatches(dateStr, leagueStr);
        
        if (!append) container.innerHTML = '';
        else document.getElementById('temp-load')?.remove();

        // Создаем группу дат (для слежения при скролле)
        const dateGroup = document.createElement('div');
        dateGroup.className = 'date-group';
        dateGroup.dataset.dateGroup = dateStr;
        
        // Добавляем красивый разделитель
        const divider = document.createElement('div');
        divider.className = 'date-divider';
        divider.innerText = new Date(dateStr).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
        dateGroup.appendChild(divider);

        if (matches.length === 0) {
            dateGroup.insertAdjacentHTML('beforeend', '<div class="no-matches">Матчей нет</div>');
        } else {
            matches.forEach(match => {
                const card = document.createElement('div');
                card.className = 'match-card';
                card.innerHTML = `
                    <div class="match-league">${match.league}</div>
                    <div class="match-content">
                        <div class="team home">${match.teamHome}</div>
                        <div class="match-info">
                            <div class="match-score">${match.score}</div>
                            <div class="match-time">${match.time}</div>
                        </div>
                        <div class="team away">${match.teamAway}</div>
                    </div>
                `;
                dateGroup.appendChild(card);
            });
        }

        container.appendChild(dateGroup);
        
        // Начинаем следить за этой группой дат
        observer.observe(dateGroup);
    }

    // Запускаем при старте
    // renderDateStrip(currentDateObj);
    //loadMatches(getFormattedDate(currentDateObj), 'ALL');
    requestAnimationFrame(() => {
    // Двойной RAF гарантирует, что браузер завершил Layout и Paint
        requestAnimationFrame(() => {
            scrollToActiveDate(false);
        });
    });
});
