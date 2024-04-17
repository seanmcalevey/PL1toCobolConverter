import os
import sys
import re


# PIPELINE: WRAPPING UP ALL FUNCTIONS TOGETHER AND PROCESSING THE TEXT WITH THEM IN ORDER
def complete_pipeline(pl1_filename, cbl_filename, counter_start):
    '''
    Method that takes all the functions in order for a complete processing pipeline, including writing 
    the output to a file of a given name passed in via 'cbl_filename' parameter.
    '''

    pl1_text = read_open_pl1_and_cobol_files(pl1_filename)
    new_pl1_text_1 = remove_comments_and_add_header(pl1_text)
    new_pl1_text_2 = general_formatting(new_pl1_text_1)
    new_pl1_text_3 = replace_pl1_expressions_and_add_periods(new_pl1_text_2, pl1_filename)
    new_pl1_text_4, counter_end = clean_up_formatting_and_increment_field_names(new_pl1_text_3, counter_start)
    final_output = write_output_to_file(new_pl1_text_4, cbl_filename)
    if final_output != '':
        print('File with name ' + cbl_filename + ' formatted successfully.')
        if counter_end and type(counter_end) is int:
            print('The incremented counter ended on ' + str(counter_end-1) + '. The next count should begin on ' 
            + str(counter_end))
        else:
            print('Incremented counting was not enabled for this conversion.')
    else:
        print('There was an issue processing file ' + cbl_filename + '.')
    
    return counter_end




# READ/STORE FILES
def read_open_pl1_and_cobol_files(filename):
    filepath = os.path.join('./', filename)
    with open(filepath, 'r') as f:
        file_text_list = f.readlines()

    return file_text_list



# INITIAL FORMATTING
def remove_comments_and_add_header(pl1_text):
    '''Bundles and processes three basic initial functions.'''

    def remove_leading_comments(pl1_text, re_exp='\/\*+\/'):
        '''Remove leading comments at top of file.'''
        
        comment_counter, beg_line, end_line = 0, 0, 0
        for i, line in enumerate(pl1_text):
            if re.search(re_exp, line):
                comment_counter += 1
                if comment_counter == 1:
                    beg_line = i
                elif comment_counter == 2:
                    end_line = i
                    break

        pl1_text = pl1_text[:beg_line] + pl1_text[end_line:]
        return pl1_text

    def remove_remaining_comments(pl1_text, re_exp='\/\*.+\*\/'):
        '''Remove in-text comments from rest of file.'''
        
        new_pl1_text = []
        for line in pl1_text:
            if (search_result := re.search(re_exp, line)):
                begin, end = search_result.span()
                length = end - begin
                spaces = ' ' * length
                new_line = re.sub(re_exp, spaces, line)
                new_pl1_text.append(new_line)
            else:
                new_pl1_text.append(line)
        return new_pl1_text
    
    def add_header_row(pl1_text, default_header_name='RECORDID'):
        '''Add header row and insert at first index in list.'''
        
        header_name, header_line_num = None, 0
        for i, line in enumerate(pl1_text):
            if (search_result := re.search('0*1\s+\w+\s*,', line)):
                begin_match, end_match = search_result.span()
                new_line = line[begin_match:end_match]
                matches = re.findall('\d+', new_line)
                if len(matches) != 1:
                    continue
                else:
                    match = matches[0]
                    try:
                        int_value = int(match)
                        if int_value == 1:
                            if (new_search := re.search('\s+\w+[\s,]', new_line)):
                                new_beg_match, new_end_match = new_search.span()
                                header_name = new_line[new_beg_match+1:new_end_match-1] # remove single spaces on edges
                                header_line_num = i
                                break
                    except:
                        continue
            
        header_name = header_name if header_name else default_header_name
        header_row = '01 ' + header_name + '.'
        seven_spaces = ' ' * 7 # seven spaces bc copybooks don't read first seven chars
        spaced_header_row = seven_spaces + header_row
        former_header_row = pl1_text.pop(header_line_num)
        pl1_text.insert(header_line_num, spaced_header_row)

        return pl1_text
    
    
    
    # MAIN PROCESS:
    new_text = remove_leading_comments(pl1_text)
    new_text = remove_remaining_comments(new_text)
    new_text = add_header_row(new_text)
    
    return new_text


# GENERAL FORMATTING
def general_formatting(pl1_text):
    '''
    Performs general formatting such as removing text to the right of the PL1 comma, globally replacing PL1 
    underscores ('_') with dashes ('-'), and inserting correct left-indentation to each row according to its 
    level number.
    '''
    

    def remove_text_after_pl1_comma_and_replace_underscores(pl1_text):
        '''
        First, strips away any remaining text after the 72nd character, so each line is a maximum of 72 chars, then 
        strips away all unnecessary information to the right of the rightmost PL1 comma in the row, and globally 
        replaces any PL1 underscores ('_') with COBOL dashes ('-').
        '''
        
        new_pl1_text = []
        for line in pl1_text:
            line = line[:72] # strip away any txt after 72nd character
            line = re.sub('_', '-', line) # global replacement
            first_position = line.find(',')
            all_matches = re.findall(',', line)
            if len(all_matches) == 0:
                semicolon_pos = line.find(';')
                if semicolon_pos >= 0:
                    new_line = line[:semicolon_pos] + '.'
                    new_pl1_text.append(new_line)
                else:
                    new_pl1_text.append(line)
            elif len(all_matches) == 1:
                new_line = line[:first_position] + '.'
                new_pl1_text.append(new_line)
            else:
                second_position = line.find(',', first_position+1) # ensures it is not the first
                new_line = line[:second_position] + '.'
                new_pl1_text.append(new_line)

        return new_pl1_text
    
    
    def add_left_formatting(pl1_text):
        '''
        Determines the indentation level by the first number in the line, and then adds the correct number of spaces 
        to match the specified indentation.
        '''

        def add_left_formatting_helper(line, number_id):
            '''
            Each row begins with 7 spaces. Then 2 more spaces are added for each successive indentation level.
            '''
            
            base_spaces = ' ' * 7
            add_spaces = lambda multiplier: ' ' * multiplier if multiplier > 0 else ''
            begin_line = line.find(str(number_id))
            new_line = line[begin_line:]
            number_of_spaces = 2 * (number_id - 1)
            new_formatting = base_spaces + add_spaces(number_of_spaces) + '0' # also adds '0' before any lvl no.
            new_line = new_formatting + new_line
            return new_line


        new_pl1_text = []
        for line in pl1_text:
            if re.search('^\s+1', line):
                new_pl1_text.append(add_left_formatting_helper(line, 1))
            elif re.search('^\s+2', line):
                new_pl1_text.append(add_left_formatting_helper(line, 2))
            elif re.search('^\s+3', line):
                new_pl1_text.append(add_left_formatting_helper(line, 3))
            elif re.search('^\s+4', line):
                new_pl1_text.append(add_left_formatting_helper(line, 4))
            elif re.search('^\s+5', line):
                new_pl1_text.append(add_left_formatting_helper(line, 5))
            elif re.search('^\s+6', line):
                new_pl1_text.append(add_left_formatting_helper(line, 6))
            elif re.search('^\s+7', line):
                new_pl1_text.append(add_left_formatting_helper(line, 7))
            elif re.search('^\s+8', line):
                new_pl1_text.append(add_left_formatting_helper(line, 8))
            elif re.search('^\s+9', line):
                new_pl1_text.append(add_left_formatting_helper(line, 9))
            else:
                new_pl1_text.append(line)
                
        return new_pl1_text
    
    
    # MAIN PROCESS:
    new_pl1_text = remove_text_after_pl1_comma_and_replace_underscores(pl1_text)
    new_pl1_text = add_left_formatting(new_pl1_text)
    
    return new_pl1_text



# REPLACE EXPRESSIONS
def replace_pl1_expressions_and_add_periods(pl1_text, pl1_filename):
    '''
    Replaces 'CHAR's with 'PIC X's and 'FIXED's with 'PIC S9's. Also reformats the 'PIC S9()V9() COMP-3' with proper 
    integers in the parentheses, taking the difference between the two 'FIXED(a,b)' integers 'a' and 'b' and inserting 
    the result into the 'S9()' parentheses and the value of 'b' into the 'V9()' parentheses.
    
    Further, lines that have information continuing onto the next line are identified, stored as 'line_holdover's, 
    and then checked on the next loop iteration if info has been stored there and combines it with the current line.
    
    Also the proper 'COMP-3's and '.'s are appended to the end of each line.
    '''
    
    line_holdover = None
    new_pl1_text = []
    for i, line in enumerate(pl1_text):

        if (search_result := re.search("\s+PIC\s*[XS]*9*['(]\d+[')]", line)):
            raise Exception(f'Line {i} in Pl1 copybook {pl1_filename} has an improper format. Please edit it.')
        
        # IMMEDIATE REPLACEMENTS/SUBSTITUTIONS
        line_sub_1 = re.sub('\sCHAR\s*\(', 'PIC X(', line)
        new_line = re.sub('\sFIXED\s*\(', 'PIC S9(', line_sub_1)
        
        # FIXED --> PIC S9
        if (search_result := re.search('\sPIC S9\(', new_line)):
            begin_match, end_match = search_result.span()
            beginning_of_line = new_line[:end_match]
            end_of_line = new_line[end_match:]
            
            # PARSE COMMA BETWEEN INTS
            if (new_search := re.search('\d+,\d+', end_of_line)):
                new_begin_match, new_end_match = new_search.span()
                line_to_search = end_of_line[new_begin_match:new_end_match]
                comma_pos = line_to_search.find(',')
                total_len, decimal_len = line_to_search[:comma_pos], line_to_search[comma_pos+1:]
                if total_len and decimal_len:
                    integer_len = int(total_len) - int(decimal_len)
                    int_len = int(total_len) if integer_len <= 0 else integer_len
                    beginning_of_line = re.sub('\.', '', beginning_of_line)
                    full_new_line = beginning_of_line + f'{int_len})V9({decimal_len}) COMP-3.'
                else:
                    raise Exception('Unknown PICS9/V9 lengths.')
            
            # NO COMMA BETWEEN INTS
            else:
                new_line = re.sub('\.', '', new_line)
                full_new_line = new_line + '  COMP-3.'
            
            # APPEND LINE W/ CHANGES
            full_new_line = line_holdover + ' ' + full_new_line.lstrip() if line_holdover else full_new_line
            new_pl1_text.append(full_new_line)
            line_holdover = None
        
        # FIXED BINARY --> PIC S9 BINARY
        elif (search_result := re.search('\sFIXED BIN\s?\(\d+\)', new_line)):
            begin_match, end_match = search_result.span()
            digit_str = re.findall('\d+', new_line[begin_match:])[0]
            digit_int = int(digit_str) if digit_str else None
            begin_new_line = new_line[:begin_match]
            if (digit_int is not None) and (type(digit_int) == int):
                if digit_int == 15:
                    full_new_line = begin_new_line + 'PIC S9(4)'
                elif digit_int == 31:
                    full_new_line = begin_new_line + 'PIC S9(8)'
                elif digit_int == 63:
                    full_new_line = begin_new_line + 'PIC S9(16)'
                else:
                    raise Exception('Unknown FIXED BINARY integer value.')
            
            full_new_line = re.sub('\.', '', full_new_line)
            full_new_line = full_new_line + ' BINARY.'
            full_new_line = line_holdover + ' ' + full_new_line.lstrip() if line_holdover else full_new_line
            new_pl1_text.append(full_new_line)
            line_holdover = None
        
        # CHAR --> PIC X
        elif (search_result := re.search('\sPIC X\(', new_line)):
            full_new_line = new_line + '.' if re.search('\.', new_line) is None else new_line
            full_new_line = line_holdover + ' ' + full_new_line.lstrip() if line_holdover else full_new_line
            new_pl1_text.append(full_new_line)
            line_holdover = None
        
        elif (search_result := re.search('\sPIC.+$', new_line)):
            full_new_line = new_line + '.' if re.search('\.', new_line) is None else new_line
            full_new_line = line_holdover + ' ' + full_new_line.lstrip() if line_holdover else full_new_line
            new_pl1_text.append(full_new_line)
            line_holdover = None

        # OCCURS CLAUSES
        elif (search_result := re.search('\d+\s+\w+\(\d+\)\s+$', new_line)):
            beg_match, end_match = search_result.span()
            new_line_2 = new_line[beg_match:end_match]
            digit_str = re.findall('\d+', new_line_2)
            end_char = re.search('\(', new_line).span()[0]
            new_line = re.sub('\.', '', new_line)
            full_new_line = new_line[:end_char] + f'  OCCURS {digit_str[0]} TIMES.'
            new_pl1_text.append(full_new_line)
            line_holdover = None
        
        # SETTING HOLDOVERS (TO BE ADDED IN FRONT OF NEXT LINE)
        # elif (search_result := re.search('\s+[^\s]+$', new_line)):
        elif (search_result := re.search('\w+[^\.]\s*$', new_line)):
            beg_match, end_match = search_result.span()

            # Only set line_holdover if the EOL match is greater than 50 chars, otherwise just append line
            new_search = re.search('\s+$', new_line)
            new_beg_match = new_search.span()[0]
            line_holdover = new_line[:new_beg_match]
        
        # ALL OTHER CASES
        else:
            new_line = new_line + '.' if new_line and re.search('\.', new_line) is None else new_line
            new_pl1_text.append(new_line)
            line_holdover = None
    
    return new_pl1_text




# FINAL FORMATTING: INCREMENT NAMES, CLEAN UP 'OCCURS' CLAUSES, AND 
def clean_up_formatting_and_increment_field_names(pl1_text, counter_start):
    '''
    Final formatting step to make sure there are no repeated field/column names, any remaining OCCURS clauses are 
    properly handled and formatted, and right-pad to 72 chars in length.
    '''
    
    def increment_field_names(pl1_text, counter_start):
        '''
        Increments a counter and adds its value to the end of each field/column name to ensure there are no 
        naming repetitions that will cause errors on the masking engine.
        '''

        counter = counter_start if counter_start > 0 else None
        new_pl1_text = []
        for line in pl1_text:
            search_result = re.search('^\s+\d{2}\s+[^\s]+', line)
            if search_result:
                beg_match, end_match = search_result.span()
                if line[:end_match][-1] == '.':
                    if counter:
                        new_line = line[:end_match-1] + '-' + str(counter) + '.'
                    else:
                        new_line = line[:end_match-1] + '.'
                else:
                    if counter:
                        cnt_len = len(str(counter))
                        add_spaces = ' ' * (3 - cnt_len) if cnt_len < 3 else ''
                        new_line = line[:end_match] + '-' + str(counter) + add_spaces + line[end_match:]
                    else:
                        new_line = line
                new_pl1_text.append(new_line)
            counter = counter + 1 if counter is not None else None
        counter_end = counter if counter is not None else 0

        return new_pl1_text, counter_end

    
    def clean_up_remaining_occurs_clauses(pl1_text):
        '''
        Searches for any 'hidden' OCCURS clauses in the form of parentheses containing one or more digits at the 
        end of a field name. If there is a match, the line is processed so that the parentheses and digits are 
        removed, and a new line with the continuing 'OCCURS X TIMES' clause is added into the list of lines.
        '''
        
        new_pl1_text = []
        for line in pl1_text:

            # Search for any remaining OCCURS structures inside parentheses following column name
            if (search_result := re.search('^\s+\d{2,}\s+[\w\-]+\(\d+\)[\d\-]{1,}', line)):
                beg_match, end_match = search_result.span()
                total_chars = end_match - beg_match
                reduced_line = line[:end_match]
                rest_of_line = line[end_match:]

                # Search for digits within parentheses at end of column name
                if (new_search := re.search('\(\d+\)[\d\-]{1,}', reduced_line)):
                    new_beg_match, new_end_match = new_search.span()
                    new_total_chars = new_end_match - new_beg_match

                    # Get both values: digits w/i parentheses (OCCURS) and digits to right of parenthesis (LINE NUMBER)
                    values = re.findall('\d+', reduced_line[new_beg_match:new_end_match])
                    if len(values) != 2:
                        raise Exception('Non-conforming format dealing with OCCURS clause.')
                    digit_str, line_num = values[0], values[1]

                    # Build new line that retains the line number and remaining info in line
                    add_spaces = ' ' * (new_total_chars - len(line_num))
                    new_line = reduced_line[:new_beg_match] + '-' + str(line_num) + add_spaces + rest_of_line[:-1]
                    new_pl1_text.append(new_line)

                    # Adds OCCURS clause as additional next line with retained digit_str info
                    additional_line = (' ' * total_chars) + f'OCCURS {digit_str} TIMES.'
                    new_pl1_text.append(additional_line)

                else:
                    new_pl1_text.append(line)

            else:
                new_pl1_text.append(line)

        return new_pl1_text

    
    def right_pad(pl1_text):
        '''
        Pads every row to 72 characters. If there are rows longer than 72 chars, the last block of text containing 
        storage information and lengths is added as a new row beneath the original one.
        '''
        
        new_pl1_text = []
        for line in pl1_text:
            new_line = line.ljust(72)
            if len(new_line) > 72:
                search = re.search('PIC\s.+$', line)
                if search:
                    begin_match, end_match = search.span()
                    first_line = line[:begin_match].ljust(72)
                    new_pl1_text.append(first_line)
                    second_line = line[begin_match:].rjust(72)
                    new_pl1_text.append(second_line)
            else:
                new_pl1_text.append(new_line)
                
        return new_pl1_text
    
    
    
    # MAIN PROCESS:
    new_pl1_text, counter_end = increment_field_names(pl1_text, counter_start)
    new_pl1_text = clean_up_remaining_occurs_clauses(new_pl1_text)
    new_pl1_text = right_pad(new_pl1_text)
    
    return new_pl1_text, counter_end




# PREPARE, GENERATE, AND WRITE NEW FILE
def write_output_to_file(pl1_text, cbl_filename):
    '''
    Writes string-type output to file, and then reads in the new file's data to make sure the file text was generated 
    properly and the file is written without error.
    '''

    def add_linebreaks_and_generate_string(pl1_text):
        '''
        
        '''
        new_pl1_text = []
        fail_line_nums_dict = {}
        for i, line in enumerate(pl1_text):

            # Confirm each line conforms to 72 character standard, or tally up the number of fails
            if len(line) != 72:
                print(f'Line number {i} NOT 72 chars:', line)
                fail_line_nums_dict[i] = line
            
            # Append linebreaks
            new_line = line + '\n'
            new_pl1_text.append(new_line)

        if len(fail_line_nums_dict) > 0:
            print('Failed line numbers:', list(fail_line_nums_dict.keys()))
            raise Exception(str(len(fail_line_nums_dict)) + ' lines have more or less than 72 characters.')

        final_output = ''.join(new_pl1_text)

        return final_output


    # Generate file output string:
    file_output_str = add_linebreaks_and_generate_string(pl1_text)

    # Write file with output str:
    filepath = os.path.join('./', cbl_filename)
    with open(filepath, 'w') as file_to_write:
        file_to_write.write(file_output_str)
    
    # Retrieve and return file for confirmation:
    with open(filepath, 'r') as confirm_file:
        file_text_confirmation = confirm_file.readlines()
    
    return file_text_confirmation





# __MAIN__ GUARD
if __name__ == '__main__':
    '''
    Main guard is used to ensure that this part of the script only executes when this file is being run as the 
    "main" file in cmd prompt/terminal (as opposed to being used to access its methods for an another task).

    Input variables passed to the script should be in the form: "script.py opt:counter file1 file2 file3 ... ".
    The first passed parameter is an optional "counter" parameter that determines where to start incrementing field 
    names from, while the rest of the passed inputs are filenames of Pl1 copybooks to be converted to COBOL. If no 
    counter integer is passed as the first argument, the script will start the incrementing counter at "1" and assume 
    all the arguments are Pl1 filenames to convert.

    N.B.: If you DO NOT want to increment field names, you may pass in "0" instead of any other positive integer. 
    Passing "0" as the first argument to the script is the only way not to increment field names. So be sure to use an 
    integer other than "0" (or nothing at all) if you wish to use the default incrementing process.
    '''

    # Script requires at least one filename parameter to run:
    if len(sys.argv) <= 1:
        raise Exception('At least one filename must be passed as a parameter.')

    try:
        # If an int is passed as the first argument to the script, begin counter on that int ...
        counter_start = int(sys.argv[1])
        list_of_pl1_filenames = sys.argv[2:]
    except:
        # ... otherwise start the counter at 1 by default.
        counter_start = 1
        list_of_pl1_filenames = sys.argv[1:]

    # Loops through pl1 file names, converts them to .cbl extension, and then calls complete_pipeline() to process:
    for pl1_filename in list_of_pl1_filenames:

        # Remove extensions and append .cbl
        if (search := re.search('\.\w{2,4}$', pl1_filename)):
            match_length = search.span()[1] - search.span()[0]
            cbl_filename = pl1_filename[:-match_length] + '.cbl'

            # Run entire pipeline of functions in order to process each file:
            counter_start = complete_pipeline(pl1_filename, cbl_filename, counter_start)
        
        else:
            raise Exception(f'{pl1_filename} was not in proper format. The filename needs to have an extension.')