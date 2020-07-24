<!-- ##    count = 0
##    yes_count = 0
##    no_count = 0
##    searches = input('Enter comma-separated search terms: ').replace(' ', '').lower().split(',')
##    print('searches')
##    print('Searching for terms:')
##    print('====================')
##    for search in searches:
##        print(search)
##    print('====================')
##    threads = 11
##    while threads > 10:
##        try:
##            threads = int(input('Enter amount of threads (Max 10): '))
##        except ValueError:
##            pass
##    start = time()
##    email_get = EmailGetter(conn, threads)
##    messages = email_get.emails
##    if messages:
##        copy_list = []
##        subject = askForBool('Search subject lines?')
##        to_ln = askForBool('Search To: lines?')
##        from_ln = askForBool('Search From: lines?')
##        process_message_searches = partial(
##            process_message,
##            subject=subject,
##            to_ln=to_ln,
##            from_ln=from_ln,
##            search_list=searches
##        )
##        print('\nProcessing messages -> ', end='')
##        with Pool() as pool:
##             for i in pool.imap_unordered(process_message_searches, messages):
##                count += 1
##                if i != False:
##                    copy_list.append(i)
##                    print('O', end='')
##                    yes_count += 1
##                else:
##                    print('X', end='')
##                    no_count += 1
##        try:
##            percent = (yes_count/no_count) * 100
##        except ZeroDivisionError:
##            percent = 0
##        end = time()
##        print('\n\n********** Finished processing emails **********')
##        print(f'Processed {count} messages in {end - start}s')
##        print(f'{percent}% ({yes_count}/{yes_count + no_count}) of messages match')
##        if len(copy_list) > 0:
##            method = ''
##            while method not in ('c', 'm', 'd'):
##                method = input('Enter whether to copy, move or display: (C, M, D): ').strip().lower()
##            print(f'Method: {method}')
##            
##            if method == 'c' or method == 'm':
##                store_folder = input('Enter storage folder: ').strip()
##                store_folder = "".join(store_folder.split())
##                if method == 'c':
##                    email_server.copy_emails(copy_list, store_folder)
##                elif method == 'm':
##                    email_server.move_emails(copy_list, store_folder)
##            elif method == 'd':
##                subjects = email_get.get_subjects(copy_list)
##                print('\nSubject Lines:')
##                print('====================')
##                for subject in subjects:
##                    print(subject)
##                print('====================')
##        else:
##            print('\nNo messages fetched...')
##
##        print('\nFinished all operations for this thread')
##        del email_get
##        del email_server      
##    else:
##        print('No messages') -->


Old buttons:

    # connect button
    connectbutton = tk.Button(
        self.root, text='Connect to server',
        command=self.connect)
    connectbutton.pack(side=tk.TOP, fill=tk.X)

    # download button
    downloadmsgs = tk.Button(
        self.root, text='Download Messages',
        command=self.download)
    downloadmsgs.pack(side=tk.TOP, fill=tk.X)

Simpledialog constructors
    tk.simpledialog.askfloat('title', 'prompt')
    tk.simpledialog.askinteger('title', 'prompt')
    tk.simpledialog.askstring('title', 'prompt')


What we're working on:
    FINDING WHY GET_EMAILS() HANGS. MUST BE BECAUSE OF THREADS, BUT WE MUST BE ABLE TO CONTROL THOSE THREADS