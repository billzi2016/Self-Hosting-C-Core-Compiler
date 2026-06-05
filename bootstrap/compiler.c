/*
 * bootstrap/compiler.c — C Core Compiler (self-hosting bootstrap)
 *
 * Compiles a C subset → portable C → calls clang.
 * Children stored as linked list (first_child / next_sibling) so that
 * parent nodes can accumulate children even while sub-nodes are being built.
 *
 * All stdlib functions declared with extern (required by Python bootstrap).
 * Error output via write(2,...) to avoid needing the stderr macro.
 */

extern int printf(char *fmt, ...);
extern int fprintf(void *stream, char *fmt, ...);
extern int sprintf(char *buf, char *fmt, ...);
extern int strcmp(char *a, char *b);
extern int strncmp(char *a, char *b, int n);
extern int strlen(char *s);
extern void *memset(void *p, int c, int n);
extern void *memcpy(void *dst, void *src, int n);
extern char *strncpy(char *dst, char *src, int n);
extern char *strcpy(char *dst, char *src);
extern int isalpha(int c);
extern int isdigit(int c);
extern int isalnum(int c);
extern int isspace(int c);
extern int atoi(char *s);
extern void *fopen(char *path, char *mode);
extern int fclose(void *fp);
extern int fread(void *buf, int sz, int n, void *fp);
extern int fseek(void *fp, int off, int whence);
extern int ftell(void *fp);
extern int fwrite(void *buf, int sz, int n, void *fp);
extern int system(char *cmd);
extern void exit(int code);
extern int write(int fd, char *buf, int n);

/* ── error helpers ───────────────────────────────────────────────────────── */

char g_errbuf[2048];

void cc_die() {
    int len;
    len = strlen(g_errbuf);
    write(2, g_errbuf, len);
    exit(1);
}

/* ── arena allocator ─────────────────────────────────────────────────────── */

char g_mem[8388608];
int  g_mem_top;

void *arena_alloc(int size) {
    void *p;
    int aligned;
    aligned = (size + 7) & (~7);
    p = (void *)(g_mem + g_mem_top);
    g_mem_top = g_mem_top + aligned;
    return p;
}

/* ── token kinds ─────────────────────────────────────────────────────────── */

int TK_EOF;
int TK_INT_LIT;
int TK_CHAR_LIT;
int TK_STR_LIT;
int TK_IDENT;
int TK_KW_INT;
int TK_KW_CHAR;
int TK_KW_VOID;
int TK_KW_RETURN;
int TK_KW_IF;
int TK_KW_ELSE;
int TK_KW_WHILE;
int TK_KW_FOR;
int TK_KW_BREAK;
int TK_KW_CONTINUE;
int TK_KW_STRUCT;
int TK_KW_TYPEDEF;
int TK_KW_SIZEOF;
int TK_KW_EXTERN;
int TK_PLUS;
int TK_MINUS;
int TK_STAR;
int TK_SLASH;
int TK_PERCENT;
int TK_AMP;
int TK_PIPE;
int TK_CARET;
int TK_TILDE;
int TK_BANG;
int TK_LT;
int TK_GT;
int TK_EQ;
int TK_LPAREN;
int TK_RPAREN;
int TK_LBRACE;
int TK_RBRACE;
int TK_LBRACKET;
int TK_RBRACKET;
int TK_SEMI;
int TK_COMMA;
int TK_DOT;
int TK_COLON;
int TK_QUESTION;
int TK_PLUS_PLUS;
int TK_MINUS_MINUS;
int TK_ARROW;
int TK_ELLIPSIS;
int TK_EQEQ;
int TK_NEQ;
int TK_LEQ;
int TK_GEQ;
int TK_AND_AND;
int TK_OR_OR;
int TK_LSHIFT;
int TK_RSHIFT;
int TK_PLUS_EQ;
int TK_MINUS_EQ;
int TK_STAR_EQ;
int TK_SLASH_EQ;

void init_token_kinds() {
    TK_EOF=0; TK_INT_LIT=1; TK_CHAR_LIT=2; TK_STR_LIT=3; TK_IDENT=4;
    TK_KW_INT=10; TK_KW_CHAR=11; TK_KW_VOID=12; TK_KW_RETURN=13;
    TK_KW_IF=14; TK_KW_ELSE=15; TK_KW_WHILE=16; TK_KW_FOR=17;
    TK_KW_BREAK=18; TK_KW_CONTINUE=19; TK_KW_STRUCT=20;
    TK_KW_TYPEDEF=21; TK_KW_SIZEOF=22; TK_KW_EXTERN=23;
    TK_PLUS=30; TK_MINUS=31; TK_STAR=32; TK_SLASH=33; TK_PERCENT=34;
    TK_AMP=35; TK_PIPE=36; TK_CARET=37; TK_TILDE=38; TK_BANG=39;
    TK_LT=40; TK_GT=41; TK_EQ=42;
    TK_LPAREN=43; TK_RPAREN=44; TK_LBRACE=45; TK_RBRACE=46;
    TK_LBRACKET=47; TK_RBRACKET=48; TK_SEMI=49; TK_COMMA=50;
    TK_DOT=51; TK_COLON=52; TK_QUESTION=53;
    TK_PLUS_PLUS=60; TK_MINUS_MINUS=61; TK_ARROW=62; TK_ELLIPSIS=63;
    TK_EQEQ=64; TK_NEQ=65; TK_LEQ=66; TK_GEQ=67;
    TK_AND_AND=68; TK_OR_OR=69; TK_LSHIFT=70; TK_RSHIFT=71;
    TK_PLUS_EQ=72; TK_MINUS_EQ=73; TK_STAR_EQ=74; TK_SLASH_EQ=75;
}

/* ── Token ───────────────────────────────────────────────────────────────── */

typedef struct Token Token;
struct Token {
    int  kind;
    char value[256];
    int  line;
    int  col;
};

typedef struct KwEntry KwEntry;
struct KwEntry {
    char word[16];
    int  kind;
};

KwEntry g_keywords[14];
int     g_kw_count;

void init_keywords() {
    int i;
    i = 0;
    strcpy(g_keywords[i].word, "int");      g_keywords[i].kind = TK_KW_INT;      i++;
    strcpy(g_keywords[i].word, "char");     g_keywords[i].kind = TK_KW_CHAR;     i++;
    strcpy(g_keywords[i].word, "void");     g_keywords[i].kind = TK_KW_VOID;     i++;
    strcpy(g_keywords[i].word, "return");   g_keywords[i].kind = TK_KW_RETURN;   i++;
    strcpy(g_keywords[i].word, "if");       g_keywords[i].kind = TK_KW_IF;       i++;
    strcpy(g_keywords[i].word, "else");     g_keywords[i].kind = TK_KW_ELSE;     i++;
    strcpy(g_keywords[i].word, "while");    g_keywords[i].kind = TK_KW_WHILE;    i++;
    strcpy(g_keywords[i].word, "for");      g_keywords[i].kind = TK_KW_FOR;      i++;
    strcpy(g_keywords[i].word, "break");    g_keywords[i].kind = TK_KW_BREAK;    i++;
    strcpy(g_keywords[i].word, "continue"); g_keywords[i].kind = TK_KW_CONTINUE; i++;
    strcpy(g_keywords[i].word, "struct");   g_keywords[i].kind = TK_KW_STRUCT;   i++;
    strcpy(g_keywords[i].word, "typedef");  g_keywords[i].kind = TK_KW_TYPEDEF;  i++;
    strcpy(g_keywords[i].word, "sizeof");   g_keywords[i].kind = TK_KW_SIZEOF;   i++;
    strcpy(g_keywords[i].word, "extern");   g_keywords[i].kind = TK_KW_EXTERN;   i++;
    g_kw_count = i;
}

int lookup_keyword(char *word) {
    int i;
    i = 0;
    while (i < g_kw_count) {
        if (strcmp(g_keywords[i].word, word) == 0) {
            return g_keywords[i].kind;
        }
        i++;
    }
    return TK_IDENT;
}

/* ── Lexer ───────────────────────────────────────────────────────────────── */

Token *g_tokens;
int    g_tok_count;

void tok_push(int kind, char *val, int line, int col) {
    Token *t;
    t = g_tokens + g_tok_count;
    t->kind = kind;
    strncpy(t->value, val, 255);
    t->value[255] = 0;
    t->line = line;
    t->col  = col;
    g_tok_count++;
}

void tokenize(char *src, int src_len) {
    int  pos;
    int  line;
    int  col;
    char ch;
    char buf[512];
    int  buf_i;
    int  kw;

    g_tokens    = (Token *)arena_alloc(65536 * (int)sizeof(Token));
    g_tok_count = 0;
    pos = 0; line = 1; col = 1;

    while (pos < src_len) {
        ch = src[pos];
        if (ch == ' ' || ch == '\t' || ch == '\r') { pos++; col++; continue; }
        if (ch == '\n') { pos++; line++; col = 1; continue; }

        /* line comment */
        if (ch == '/' && pos+1 < src_len && src[pos+1] == '/') {
            while (pos < src_len && src[pos] != '\n') { pos++; }
            continue;
        }
        /* block comment */
        if (ch == '/' && pos+1 < src_len && src[pos+1] == '*') {
            pos += 2; col += 2;
            while (pos < src_len) {
                if (src[pos] == '*' && pos+1 < src_len && src[pos+1] == '/') {
                    pos += 2; col += 2; break;
                }
                if (src[pos] == '\n') { line++; col = 1; } else { col++; }
                pos++;
            }
            continue;
        }
        /* string literal */
        if (ch == '"') {
            buf_i = 0; pos++; col++;
            while (pos < src_len && src[pos] != '"') {
                if (src[pos] == '\\' && pos+1 < src_len) {
                    buf[buf_i++] = '\\'; pos++; col++;
                    buf[buf_i++] = src[pos]; pos++; col++;
                } else {
                    buf[buf_i++] = src[pos]; pos++; col++;
                }
            }
            buf[buf_i] = 0; pos++; col++;
            tok_push(TK_STR_LIT, buf, line, col);
            continue;
        }
        /* char literal */
        if (ch == '\'') {
            buf_i = 0; pos++; col++;
            while (pos < src_len && src[pos] != '\'') {
                if (src[pos] == '\\' && pos+1 < src_len) {
                    buf[buf_i++] = '\\'; pos++; col++;
                    buf[buf_i++] = src[pos]; pos++; col++;
                } else {
                    buf[buf_i++] = src[pos]; pos++; col++;
                }
            }
            buf[buf_i] = 0; pos++; col++;
            tok_push(TK_CHAR_LIT, buf, line, col);
            continue;
        }
        /* number */
        if (isdigit((int)ch)) {
            buf_i = 0;
            if (ch == '0' && pos+1 < src_len && (src[pos+1] == 'x' || src[pos+1] == 'X')) {
                buf[buf_i++] = src[pos++]; col++;
                buf[buf_i++] = src[pos++]; col++;
                while (pos < src_len) {
                    char hc; hc = src[pos];
                    if (isdigit((int)hc) || (hc>='a'&&hc<='f') || (hc>='A'&&hc<='F')) {
                        buf[buf_i++] = hc; pos++; col++;
                    } else { break; }
                }
            } else {
                while (pos < src_len && isdigit((int)src[pos])) {
                    buf[buf_i++] = src[pos++]; col++;
                }
            }
            buf[buf_i] = 0;
            tok_push(TK_INT_LIT, buf, line, col);
            continue;
        }
        /* identifier / keyword */
        if (isalpha((int)ch) || ch == '_') {
            buf_i = 0;
            while (pos < src_len && (isalnum((int)src[pos]) || src[pos] == '_')) {
                buf[buf_i++] = src[pos++]; col++;
            }
            buf[buf_i] = 0;
            kw = lookup_keyword(buf);
            tok_push(kw, buf, line, col);
            continue;
        }
        /* three-char */
        if (pos+2 < src_len && ch=='.' && src[pos+1]=='.' && src[pos+2]=='.') {
            tok_push(TK_ELLIPSIS,"...",line,col); pos+=3; col+=3; continue;
        }
        /* two-char */
        if (pos+1 < src_len) {
            char c2; c2 = src[pos+1];
            if (ch=='+'&&c2=='+'){tok_push(TK_PLUS_PLUS, "++",line,col);pos+=2;col+=2;continue;}
            if (ch=='-'&&c2=='-'){tok_push(TK_MINUS_MINUS,"--",line,col);pos+=2;col+=2;continue;}
            if (ch=='-'&&c2=='>'){tok_push(TK_ARROW,     "->",line,col);pos+=2;col+=2;continue;}
            if (ch=='='&&c2=='='){tok_push(TK_EQEQ,      "==",line,col);pos+=2;col+=2;continue;}
            if (ch=='!'&&c2=='='){tok_push(TK_NEQ,       "!=",line,col);pos+=2;col+=2;continue;}
            if (ch=='<'&&c2=='='){tok_push(TK_LEQ,       "<=",line,col);pos+=2;col+=2;continue;}
            if (ch=='>'&&c2=='='){tok_push(TK_GEQ,       ">=",line,col);pos+=2;col+=2;continue;}
            if (ch=='&'&&c2=='&'){tok_push(TK_AND_AND,   "&&",line,col);pos+=2;col+=2;continue;}
            if (ch=='|'&&c2=='|'){tok_push(TK_OR_OR,     "||",line,col);pos+=2;col+=2;continue;}
            if (ch=='<'&&c2=='<'){tok_push(TK_LSHIFT,    "<<",line,col);pos+=2;col+=2;continue;}
            if (ch=='>'&&c2=='>'){tok_push(TK_RSHIFT,    ">>",line,col);pos+=2;col+=2;continue;}
            if (ch=='+'&&c2=='='){tok_push(TK_PLUS_EQ,   "+=",line,col);pos+=2;col+=2;continue;}
            if (ch=='-'&&c2=='='){tok_push(TK_MINUS_EQ,  "-=",line,col);pos+=2;col+=2;continue;}
            if (ch=='*'&&c2=='='){tok_push(TK_STAR_EQ,   "*=",line,col);pos+=2;col+=2;continue;}
            if (ch=='/'&&c2=='='){tok_push(TK_SLASH_EQ,  "/=",line,col);pos+=2;col+=2;continue;}
        }
        /* single-char */
        buf[0] = ch; buf[1] = 0;
        if (ch=='+'){tok_push(TK_PLUS,    buf,line,col);pos++;col++;continue;}
        if (ch=='-'){tok_push(TK_MINUS,   buf,line,col);pos++;col++;continue;}
        if (ch=='*'){tok_push(TK_STAR,    buf,line,col);pos++;col++;continue;}
        if (ch=='/'){tok_push(TK_SLASH,   buf,line,col);pos++;col++;continue;}
        if (ch=='%'){tok_push(TK_PERCENT, buf,line,col);pos++;col++;continue;}
        if (ch=='&'){tok_push(TK_AMP,     buf,line,col);pos++;col++;continue;}
        if (ch=='|'){tok_push(TK_PIPE,    buf,line,col);pos++;col++;continue;}
        if (ch=='^'){tok_push(TK_CARET,   buf,line,col);pos++;col++;continue;}
        if (ch=='~'){tok_push(TK_TILDE,   buf,line,col);pos++;col++;continue;}
        if (ch=='!'){tok_push(TK_BANG,    buf,line,col);pos++;col++;continue;}
        if (ch=='<'){tok_push(TK_LT,      buf,line,col);pos++;col++;continue;}
        if (ch=='>'){tok_push(TK_GT,      buf,line,col);pos++;col++;continue;}
        if (ch=='='){tok_push(TK_EQ,      buf,line,col);pos++;col++;continue;}
        if (ch=='('){tok_push(TK_LPAREN,  buf,line,col);pos++;col++;continue;}
        if (ch==')'){tok_push(TK_RPAREN,  buf,line,col);pos++;col++;continue;}
        if (ch=='{'){tok_push(TK_LBRACE,  buf,line,col);pos++;col++;continue;}
        if (ch=='}'){tok_push(TK_RBRACE,  buf,line,col);pos++;col++;continue;}
        if (ch=='['){tok_push(TK_LBRACKET,buf,line,col);pos++;col++;continue;}
        if (ch==']'){tok_push(TK_RBRACKET,buf,line,col);pos++;col++;continue;}
        if (ch==';'){tok_push(TK_SEMI,    buf,line,col);pos++;col++;continue;}
        if (ch==','){tok_push(TK_COMMA,   buf,line,col);pos++;col++;continue;}
        if (ch=='.'){tok_push(TK_DOT,     buf,line,col);pos++;col++;continue;}
        if (ch==':'){tok_push(TK_COLON,   buf,line,col);pos++;col++;continue;}
        if (ch=='?'){tok_push(TK_QUESTION,buf,line,col);pos++;col++;continue;}
        sprintf(g_errbuf,"Lex error: unknown char '%c' at line %d\n",ch,line);
        cc_die();
    }
    tok_push(TK_EOF, "", line, col);
}

/* ── AST node kinds ──────────────────────────────────────────────────────── */

int NK_NULL;
int NK_PROGRAM;
int NK_FUNC_DECL;
int NK_FUNC_PROTO;
int NK_GLOBAL_VAR;
int NK_STRUCT_DECL;
int NK_TYPEDEF_DECL;
int NK_PARAM;
int NK_STRUCT_FIELD;
int NK_BLOCK;
int NK_VAR_DECL;
int NK_RETURN;
int NK_IF;
int NK_WHILE;
int NK_FOR;
int NK_BREAK;
int NK_CONTINUE;
int NK_EXPR_STMT;
int NK_ASSIGN;
int NK_BINOP;
int NK_UNARY;
int NK_POSTFIX_INC;
int NK_CALL;
int NK_INDEX;
int NK_MEMBER;
int NK_CAST;
int NK_SIZEOF_EXPR;
int NK_SIZEOF_TYPE;
int NK_TERNARY;
int NK_INT_LIT;
int NK_CHAR_LIT;
int NK_STR_LIT;
int NK_IDENT_REF;
int NK_ADDR_OF;
int NK_DEREF;

void init_node_kinds() {
    NK_NULL=0; NK_PROGRAM=1; NK_FUNC_DECL=2; NK_FUNC_PROTO=3;
    NK_GLOBAL_VAR=4; NK_STRUCT_DECL=5; NK_TYPEDEF_DECL=6;
    NK_PARAM=7; NK_STRUCT_FIELD=8;
    NK_BLOCK=10; NK_VAR_DECL=11; NK_RETURN=12; NK_IF=13;
    NK_WHILE=14; NK_FOR=15; NK_BREAK=16; NK_CONTINUE=17; NK_EXPR_STMT=18;
    NK_ASSIGN=20; NK_BINOP=21; NK_UNARY=22; NK_POSTFIX_INC=23;
    NK_CALL=24; NK_INDEX=25; NK_MEMBER=26; NK_CAST=27;
    NK_SIZEOF_EXPR=28; NK_SIZEOF_TYPE=29; NK_TERNARY=30;
    NK_INT_LIT=31; NK_CHAR_LIT=32; NK_STR_LIT=33;
    NK_IDENT_REF=34; NK_ADDR_OF=35; NK_DEREF=36;
}

/* ── AST Node ────────────────────────────────────────────────────────────── */

typedef struct Node Node;
struct Node {
    int  kind;

    char type_base[32];
    int  type_ptr;
    int  type_arr;
    char struct_name[32];
    int  type_is_void;

    char name[256];

    int  is_extern;
    int  is_variadic;
    int  is_arrow;
    int  op_is_post;
    int  op_sign;

    int  ival;

    /* linked-list child storage */
    int  first_child;
    int  last_child;
    int  next_sibling;
    int  child_count;
};

Node g_nodes[65536];
int  g_node_count;

void init_nodes() {
    /* node 0 is the permanent null node */
    g_node_count = 1;
    memset((void *)g_nodes, 0, (int)sizeof(Node));
    g_nodes[0].kind         = 0;
    g_nodes[0].first_child  = 0;
    g_nodes[0].last_child   = 0;
    g_nodes[0].next_sibling = 0;
}

int new_node(int kind) {
    int idx;
    idx = g_node_count;
    g_node_count++;
    memset((void *)(g_nodes + idx), 0, (int)sizeof(Node));
    g_nodes[idx].kind         = kind;
    g_nodes[idx].first_child  = 0;
    g_nodes[idx].last_child   = 0;
    g_nodes[idx].next_sibling = 0;
    return idx;
}

void node_add_child(int parent, int child) {
    /* child == 0 means null node — still link it */
    g_nodes[child].next_sibling = 0;
    if (g_nodes[parent].first_child == 0) {
        g_nodes[parent].first_child = child;
        g_nodes[parent].last_child  = child;
    } else {
        g_nodes[g_nodes[parent].last_child].next_sibling = child;
        g_nodes[parent].last_child = child;
    }
    g_nodes[parent].child_count++;
}

int node_get_child(int parent, int i) {
    int cur;
    int j;
    cur = g_nodes[parent].first_child;
    j = 0;
    while (j < i) {
        cur = g_nodes[cur].next_sibling;
        j++;
    }
    return cur;
}

/* ── typedef / struct name tables ────────────────────────────────────────── */

char g_typedef_names[512][64];
int  g_typedef_count;

int is_typedef_name(char *s) {
    int i;
    i = 0;
    while (i < g_typedef_count) {
        if (strcmp(g_typedef_names[i], s) == 0) { return 1; }
        i++;
    }
    return 0;
}

void register_typedef(char *s) {
    strncpy(g_typedef_names[g_typedef_count], s, 63);
    g_typedef_names[g_typedef_count][63] = 0;
    g_typedef_count++;
}

/* ── Parser state ────────────────────────────────────────────────────────── */

int g_cur;

int cur_kind()  { return g_tokens[g_cur].kind; }
char *cur_val() { return g_tokens[g_cur].value; }
int cur_line()  { return g_tokens[g_cur].line; }

void advance() { g_cur++; }

void parse_error(char *msg) {
    sprintf(g_errbuf,"Parse error line %d token '%s': %s\n",
            cur_line(), cur_val(), msg);
    cc_die();
}

void expect(int kind) {
    if (cur_kind() != kind) {
        sprintf(g_errbuf,"Expected token %d, got %d ('%s') line %d\n",
                kind, cur_kind(), cur_val(), cur_line());
        cc_die();
    }
    advance();
}

int peek_kind(int off) { return g_tokens[g_cur + off].kind; }

int is_type_start() {
    int k; k = cur_kind();
    if (k==TK_KW_INT||k==TK_KW_CHAR||k==TK_KW_VOID) return 1;
    if (k==TK_KW_STRUCT||k==TK_KW_EXTERN) return 1;
    if (k==TK_IDENT && is_typedef_name(cur_val())) return 1;
    return 0;
}

void parse_type_into(int n) {
    int k; k = cur_kind();
    g_nodes[n].is_extern = 0;
    if (k == TK_KW_EXTERN) { g_nodes[n].is_extern = 1; advance(); k = cur_kind(); }
    if (k == TK_KW_INT) {
        strcpy(g_nodes[n].type_base,"int"); advance();
    } else if (k == TK_KW_CHAR) {
        strcpy(g_nodes[n].type_base,"char"); advance();
    } else if (k == TK_KW_VOID) {
        strcpy(g_nodes[n].type_base,"void"); g_nodes[n].type_is_void=1; advance();
    } else if (k == TK_KW_STRUCT) {
        advance(); strcpy(g_nodes[n].type_base,"struct");
        if (cur_kind()==TK_IDENT) { strcpy(g_nodes[n].struct_name,cur_val()); advance(); }
    } else if (k==TK_IDENT && is_typedef_name(cur_val())) {
        strcpy(g_nodes[n].type_base,cur_val()); advance();
    } else { parse_error("expected type specifier"); }
    while (cur_kind()==TK_STAR) { g_nodes[n].type_ptr++; advance(); }
}

int parse_type_node() {
    int n; n = new_node(0); parse_type_into(n); return n;
}

/* forward declarations */
int parse_unary();
int parse_expr();
int parse_stmt();
int parse_block();

/* ── Expressions ─────────────────────────────────────────────────────────── */

int parse_primary() {
    int k; int n; k = cur_kind();

    if (k == TK_INT_LIT) {
        char *v;
        n = new_node(NK_INT_LIT); v = cur_val();
        if (v[0]=='0' && (v[1]=='x'||v[1]=='X')) {
            int i; int acc; acc=0; i=2;
            while (v[i]) {
                acc *= 16;
                if (v[i]>='0'&&v[i]<='9') acc += v[i]-'0';
                else if (v[i]>='a'&&v[i]<='f') acc += v[i]-'a'+10;
                else acc += v[i]-'A'+10;
                i++;
            }
            g_nodes[n].ival = acc;
        } else { g_nodes[n].ival = atoi(v); }
        advance(); return n;
    }
    if (k == TK_CHAR_LIT) {
        char *v; int val;
        n = new_node(NK_CHAR_LIT); v = cur_val(); val=0;
        if (v[0]=='\\') {
            if (v[1]=='n') val=10;
            else if (v[1]=='t') val=9;
            else if (v[1]=='r') val=13;
            else if (v[1]=='0') val=0;
            else if (v[1]=='\\') val=92;
            else if (v[1]=='\'') val=39;
            else if (v[1]=='"') val=34;
            else val=v[1];
        } else { val=(int)v[0]; }
        g_nodes[n].ival = val; advance(); return n;
    }
    if (k == TK_STR_LIT) {
        n = new_node(NK_STR_LIT);
        strcpy(g_nodes[n].name, cur_val()); advance(); return n;
    }
    if (k == TK_IDENT) {
        n = new_node(NK_IDENT_REF);
        strcpy(g_nodes[n].name, cur_val()); advance(); return n;
    }
    if (k == TK_LPAREN) {
        advance();
        if (is_type_start()) {
            int tn; int inner; int cn;
            tn = parse_type_node(); expect(TK_RPAREN);
            inner = parse_unary();
            cn = new_node(NK_CAST);
            strcpy(g_nodes[cn].type_base,   g_nodes[tn].type_base);
            strcpy(g_nodes[cn].struct_name, g_nodes[tn].struct_name);
            g_nodes[cn].type_ptr     = g_nodes[tn].type_ptr;
            g_nodes[cn].type_is_void = g_nodes[tn].type_is_void;
            node_add_child(cn, inner); return cn;
        } else {
            int e; e = parse_expr(); expect(TK_RPAREN); return e;
        }
    }
    if (k == TK_KW_SIZEOF) {
        advance(); expect(TK_LPAREN);
        if (is_type_start()) {
            int tn; int sn;
            tn = parse_type_node(); expect(TK_RPAREN);
            sn = new_node(NK_SIZEOF_TYPE);
            strcpy(g_nodes[sn].type_base,   g_nodes[tn].type_base);
            strcpy(g_nodes[sn].struct_name, g_nodes[tn].struct_name);
            g_nodes[sn].type_ptr = g_nodes[tn].type_ptr; return sn;
        } else {
            int e; int sn;
            e = parse_expr(); expect(TK_RPAREN);
            sn = new_node(NK_SIZEOF_EXPR); node_add_child(sn,e); return sn;
        }
    }
    parse_error("unexpected token in expression"); return 0;
}

int parse_postfix() {
    int e; e = parse_primary();
    while (1) {
        int k; k = cur_kind();
        if (k == TK_LBRACKET) {
            int idx_n; int idx_e;
            advance(); idx_e = parse_expr(); expect(TK_RBRACKET);
            idx_n = new_node(NK_INDEX);
            node_add_child(idx_n, e); node_add_child(idx_n, idx_e); e = idx_n;
        } else if (k==TK_DOT || k==TK_ARROW) {
            int mn; int is_arr; is_arr=(k==TK_ARROW); advance();
            mn = new_node(NK_MEMBER); g_nodes[mn].is_arrow=is_arr;
            if (cur_kind()!=TK_IDENT) { parse_error("expected member name"); }
            strcpy(g_nodes[mn].name,cur_val()); advance();
            node_add_child(mn, e); e = mn;
        } else if (k == TK_PLUS_PLUS) {
            int pn; advance();
            pn = new_node(NK_POSTFIX_INC); g_nodes[pn].op_is_post=1; g_nodes[pn].op_sign=1;
            node_add_child(pn,e); e=pn;
        } else if (k == TK_MINUS_MINUS) {
            int pn; advance();
            pn = new_node(NK_POSTFIX_INC); g_nodes[pn].op_is_post=1; g_nodes[pn].op_sign=-1;
            node_add_child(pn,e); e=pn;
        } else if (k == TK_LPAREN) {
            int cn; advance();
            cn = new_node(NK_CALL); node_add_child(cn, e);
            if (cur_kind()!=TK_RPAREN) {
                node_add_child(cn, parse_expr());
                while (cur_kind()==TK_COMMA) { advance(); node_add_child(cn,parse_expr()); }
            }
            expect(TK_RPAREN); e=cn;
        } else { break; }
    }
    return e;
}

int parse_unary() {
    int k; k = cur_kind();
    if (k==TK_MINUS) {
        int n; advance(); n=new_node(NK_UNARY); strcpy(g_nodes[n].name,"-");
        node_add_child(n,parse_unary()); return n;
    }
    if (k==TK_BANG) {
        int n; advance(); n=new_node(NK_UNARY); strcpy(g_nodes[n].name,"!");
        node_add_child(n,parse_unary()); return n;
    }
    if (k==TK_TILDE) {
        int n; advance(); n=new_node(NK_UNARY); strcpy(g_nodes[n].name,"~");
        node_add_child(n,parse_unary()); return n;
    }
    if (k==TK_STAR) {
        int n; advance(); n=new_node(NK_DEREF); node_add_child(n,parse_unary()); return n;
    }
    if (k==TK_AMP) {
        int n; advance(); n=new_node(NK_ADDR_OF); node_add_child(n,parse_unary()); return n;
    }
    if (k==TK_PLUS_PLUS) {
        int n; advance(); n=new_node(NK_POSTFIX_INC); g_nodes[n].op_is_post=0; g_nodes[n].op_sign=1;
        node_add_child(n,parse_unary()); return n;
    }
    if (k==TK_MINUS_MINUS) {
        int n; advance(); n=new_node(NK_POSTFIX_INC); g_nodes[n].op_is_post=0; g_nodes[n].op_sign=-1;
        node_add_child(n,parse_unary()); return n;
    }
    return parse_postfix();
}

int parse_mul() {
    int e; e = parse_unary();
    while (cur_kind()==TK_STAR||cur_kind()==TK_SLASH||cur_kind()==TK_PERCENT) {
        int n; char op[4];
        if (cur_kind()==TK_STAR) strcpy(op,"*");
        else if (cur_kind()==TK_SLASH) strcpy(op,"/");
        else strcpy(op,"%");
        advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,op);
        node_add_child(n,e); node_add_child(n,parse_unary()); e=n;
    }
    return e;
}
int parse_add() {
    int e; e = parse_mul();
    while (cur_kind()==TK_PLUS||cur_kind()==TK_MINUS) {
        int n; char op[4];
        if (cur_kind()==TK_PLUS) strcpy(op,"+"); else strcpy(op,"-");
        advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,op);
        node_add_child(n,e); node_add_child(n,parse_mul()); e=n;
    }
    return e;
}
int parse_shift() {
    int e; e = parse_add();
    while (cur_kind()==TK_LSHIFT||cur_kind()==TK_RSHIFT) {
        int n; char op[4];
        if (cur_kind()==TK_LSHIFT) strcpy(op,"<<"); else strcpy(op,">>");
        advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,op);
        node_add_child(n,e); node_add_child(n,parse_add()); e=n;
    }
    return e;
}
int parse_relational() {
    int e; e = parse_shift();
    while (cur_kind()==TK_LT||cur_kind()==TK_GT||
           cur_kind()==TK_LEQ||cur_kind()==TK_GEQ) {
        int n; char op[4];
        if (cur_kind()==TK_LT) strcpy(op,"<");
        else if (cur_kind()==TK_GT) strcpy(op,">");
        else if (cur_kind()==TK_LEQ) strcpy(op,"<=");
        else strcpy(op,">=");
        advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,op);
        node_add_child(n,e); node_add_child(n,parse_shift()); e=n;
    }
    return e;
}
int parse_equality() {
    int e; e = parse_relational();
    while (cur_kind()==TK_EQEQ||cur_kind()==TK_NEQ) {
        int n; char op[4];
        if (cur_kind()==TK_EQEQ) strcpy(op,"=="); else strcpy(op,"!=");
        advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,op);
        node_add_child(n,e); node_add_child(n,parse_relational()); e=n;
    }
    return e;
}
int parse_bitand() {
    int e; e = parse_equality();
    while (cur_kind()==TK_AMP) {
        int n; advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,"&");
        node_add_child(n,e); node_add_child(n,parse_equality()); e=n;
    }
    return e;
}
int parse_bitxor() {
    int e; e = parse_bitand();
    while (cur_kind()==TK_CARET) {
        int n; advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,"^");
        node_add_child(n,e); node_add_child(n,parse_bitand()); e=n;
    }
    return e;
}
int parse_bitor() {
    int e; e = parse_bitxor();
    while (cur_kind()==TK_PIPE) {
        int n; advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,"|");
        node_add_child(n,e); node_add_child(n,parse_bitxor()); e=n;
    }
    return e;
}
int parse_logand() {
    int e; e = parse_bitor();
    while (cur_kind()==TK_AND_AND) {
        int n; advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,"&&");
        node_add_child(n,e); node_add_child(n,parse_bitor()); e=n;
    }
    return e;
}
int parse_logor() {
    int e; e = parse_logand();
    while (cur_kind()==TK_OR_OR) {
        int n; advance(); n=new_node(NK_BINOP); strcpy(g_nodes[n].name,"||");
        node_add_child(n,e); node_add_child(n,parse_logand()); e=n;
    }
    return e;
}
int parse_ternary() {
    int e; e = parse_logor();
    if (cur_kind()==TK_QUESTION) {
        int tn; int then_e; int else_e; advance();
        then_e = parse_expr(); expect(TK_COLON); else_e = parse_ternary();
        tn = new_node(NK_TERNARY);
        node_add_child(tn,e); node_add_child(tn,then_e); node_add_child(tn,else_e);
        return tn;
    }
    return e;
}
int parse_assign() {
    int e; e = parse_ternary();
    if (cur_kind()==TK_EQ) {
        int an; advance(); an=new_node(NK_ASSIGN); strcpy(g_nodes[an].name,"=");
        node_add_child(an,e); node_add_child(an,parse_assign()); return an;
    }
    if (cur_kind()==TK_PLUS_EQ||cur_kind()==TK_MINUS_EQ||
        cur_kind()==TK_STAR_EQ||cur_kind()==TK_SLASH_EQ) {
        int an; char op[4];
        if (cur_kind()==TK_PLUS_EQ) strcpy(op,"+=");
        else if (cur_kind()==TK_MINUS_EQ) strcpy(op,"-=");
        else if (cur_kind()==TK_STAR_EQ) strcpy(op,"*=");
        else strcpy(op,"/=");
        advance(); an=new_node(NK_ASSIGN); strcpy(g_nodes[an].name,op);
        node_add_child(an,e); node_add_child(an,parse_assign()); return an;
    }
    return e;
}
int parse_expr() { return parse_assign(); }

/* ── Statements ──────────────────────────────────────────────────────────── */

int parse_block() {
    int bn; expect(TK_LBRACE); bn=new_node(NK_BLOCK);
    while (cur_kind()!=TK_RBRACE && cur_kind()!=TK_EOF) {
        node_add_child(bn, parse_stmt());
    }
    expect(TK_RBRACE); return bn;
}

int parse_stmt() {
    int k; k = cur_kind();
    if (k==TK_LBRACE) { return parse_block(); }
    if (k==TK_KW_RETURN) {
        int rn; advance(); rn=new_node(NK_RETURN);
        if (cur_kind()!=TK_SEMI) { node_add_child(rn,parse_expr()); }
        expect(TK_SEMI); return rn;
    }
    if (k==TK_KW_BREAK)    { int n; advance(); expect(TK_SEMI); n=new_node(NK_BREAK); return n; }
    if (k==TK_KW_CONTINUE) { int n; advance(); expect(TK_SEMI); n=new_node(NK_CONTINUE); return n; }
    if (k==TK_KW_IF) {
        int n; advance(); expect(TK_LPAREN); n=new_node(NK_IF);
        node_add_child(n,parse_expr()); expect(TK_RPAREN);
        node_add_child(n,parse_stmt());
        if (cur_kind()==TK_KW_ELSE) { advance(); node_add_child(n,parse_stmt()); }
        return n;
    }
    if (k==TK_KW_WHILE) {
        int n; advance(); expect(TK_LPAREN); n=new_node(NK_WHILE);
        node_add_child(n,parse_expr()); expect(TK_RPAREN);
        node_add_child(n,parse_stmt()); return n;
    }
    if (k==TK_KW_FOR) {
        int n; advance(); expect(TK_LPAREN); n=new_node(NK_FOR);
        /* init */
        if (cur_kind()==TK_SEMI) { node_add_child(n,0); advance(); }
        else if (is_type_start()) { node_add_child(n,parse_stmt()); }
        else {
            int es; es=new_node(NK_EXPR_STMT); node_add_child(es,parse_expr());
            node_add_child(n,es); expect(TK_SEMI);
        }
        /* cond */
        if (cur_kind()==TK_SEMI) { node_add_child(n,0); }
        else { node_add_child(n,parse_expr()); }
        expect(TK_SEMI);
        /* inc */
        if (cur_kind()==TK_RPAREN) { node_add_child(n,0); }
        else { node_add_child(n,parse_expr()); }
        expect(TK_RPAREN);
        node_add_child(n,parse_stmt()); return n;
    }
    if (is_type_start()) {
        int vn; int arr; vn=new_node(NK_VAR_DECL); parse_type_into(vn);
        if (cur_kind()!=TK_IDENT) { parse_error("expected variable name"); }
        strcpy(g_nodes[vn].name,cur_val()); advance();
        arr=0;
        if (cur_kind()==TK_LBRACKET) {
            advance();
            if (cur_kind()==TK_INT_LIT) { arr=atoi(cur_val()); advance(); }
            expect(TK_RBRACKET);
        }
        g_nodes[vn].type_arr=arr;
        if (cur_kind()==TK_EQ) { advance(); node_add_child(vn,parse_expr()); }
        expect(TK_SEMI); return vn;
    }
    {
        int es; es=new_node(NK_EXPR_STMT);
        node_add_child(es,parse_expr()); expect(TK_SEMI); return es;
    }
}

/* ── Parameters ──────────────────────────────────────────────────────────── */

void parse_params(int func_node) {
    if (cur_kind()==TK_RPAREN) return;
    if (cur_kind()==TK_KW_VOID && peek_kind(1)==TK_RPAREN) { advance(); return; }
    while (1) {
        int pn;
        if (cur_kind()==TK_ELLIPSIS) { advance(); g_nodes[func_node].is_variadic=1; break; }
        pn=new_node(NK_PARAM); parse_type_into(pn);
        if (cur_kind()==TK_IDENT) { strcpy(g_nodes[pn].name,cur_val()); advance(); }
        if (cur_kind()==TK_LBRACKET) {
            advance();
            if (cur_kind()==TK_INT_LIT) { g_nodes[pn].type_arr=atoi(cur_val()); advance(); }
            expect(TK_RBRACKET);
        }
        node_add_child(func_node,pn);
        if (cur_kind()!=TK_COMMA) break;
        advance();
    }
}

/* ── Struct body ─────────────────────────────────────────────────────────── */

int parse_struct_body(char *tag) {
    int sn; sn=new_node(NK_STRUCT_DECL);
    if (tag!=(char*)0) strcpy(g_nodes[sn].name,tag);
    expect(TK_LBRACE);
    while (cur_kind()!=TK_RBRACE && cur_kind()!=TK_EOF) {
        int fn; fn=new_node(NK_STRUCT_FIELD); parse_type_into(fn);
        if (cur_kind()!=TK_IDENT) { parse_error("expected field name"); }
        strcpy(g_nodes[fn].name,cur_val()); advance();
        if (cur_kind()==TK_LBRACKET) {
            advance();
            if (cur_kind()==TK_INT_LIT) { g_nodes[fn].type_arr=atoi(cur_val()); advance(); }
            expect(TK_RBRACKET);
        }
        expect(TK_SEMI); node_add_child(sn,fn);
    }
    expect(TK_RBRACE); return sn;
}

/* ── Top-level declarations ──────────────────────────────────────────────── */

int parse_top_level() {
    int is_ext; int ptr_level;
    char base[32]; char stag[64]; char dname[256];
    int i;

    is_ext=0; ptr_level=0;
    i=0; while(i<32){base[i]=0;i++;}
    i=0; while(i<64){stag[i]=0;i++;}
    i=0; while(i<256){dname[i]=0;i++;}

    /* typedef */
    if (cur_kind()==TK_KW_TYPEDEF) {
        advance();
        if (cur_kind()==TK_KW_STRUCT) {
            int has_tag; advance(); has_tag=0;
            if (cur_kind()==TK_IDENT && !is_typedef_name(cur_val())) {
                if (peek_kind(1)==TK_LBRACE || peek_kind(1)==TK_IDENT) {
                    strcpy(stag,cur_val()); has_tag=1; advance();
                }
            }
            if (cur_kind()==TK_LBRACE) {
                int sn; char *tp; tp=(char*)0;
                if (has_tag) tp=stag;
                sn=parse_struct_body(tp);
                g_nodes[sn].kind=NK_TYPEDEF_DECL;
                if (cur_kind()!=TK_IDENT) { parse_error("expected typedef alias"); }
                strcpy(g_nodes[sn].struct_name,cur_val());
                register_typedef(cur_val()); advance(); expect(TK_SEMI); return sn;
            } else {
                int tn; tn=new_node(NK_TYPEDEF_DECL);
                strcpy(g_nodes[tn].type_base,"struct");
                if (has_tag) strcpy(g_nodes[tn].name,stag);
                if (cur_kind()!=TK_IDENT) { parse_error("expected typedef alias"); }
                strcpy(g_nodes[tn].struct_name,cur_val());
                register_typedef(cur_val()); advance(); expect(TK_SEMI); return tn;
            }
        } else {
            int tn; tn=new_node(NK_TYPEDEF_DECL); parse_type_into(tn);
            if (cur_kind()!=TK_IDENT) { parse_error("expected typedef alias"); }
            strcpy(g_nodes[tn].struct_name,cur_val());
            register_typedef(cur_val()); advance(); expect(TK_SEMI); return tn;
        }
    }

    /* plain struct Tag { }; */
    if (cur_kind()==TK_KW_STRUCT && peek_kind(1)==TK_IDENT && peek_kind(2)==TK_LBRACE) {
        int sn; advance(); strcpy(stag,cur_val()); advance();
        sn=parse_struct_body(stag); expect(TK_SEMI); return sn;
    }

    /* extern */
    if (cur_kind()==TK_KW_EXTERN) { is_ext=1; advance(); }

    /* base type */
    if (cur_kind()==TK_KW_INT)         { strcpy(base,"int");   advance(); }
    else if (cur_kind()==TK_KW_CHAR)   { strcpy(base,"char");  advance(); }
    else if (cur_kind()==TK_KW_VOID)   { strcpy(base,"void");  advance(); }
    else if (cur_kind()==TK_KW_STRUCT) {
        advance(); strcpy(base,"struct");
        if (cur_kind()==TK_IDENT) { strcpy(stag,cur_val()); advance(); }
    } else if (cur_kind()==TK_IDENT && is_typedef_name(cur_val())) {
        strcpy(base,cur_val()); advance();
    } else { parse_error("expected type at top level"); }

    while (cur_kind()==TK_STAR) { ptr_level++; advance(); }
    if (cur_kind()!=TK_IDENT) { parse_error("expected name after type"); }
    strcpy(dname,cur_val()); advance();

    if (cur_kind()==TK_LPAREN) {
        int fn; advance(); fn=new_node(NK_FUNC_DECL);
        strcpy(g_nodes[fn].type_base,base);
        strcpy(g_nodes[fn].struct_name,stag);
        g_nodes[fn].type_ptr=ptr_level; g_nodes[fn].is_extern=is_ext;
        strcpy(g_nodes[fn].name,dname);
        if (strcmp(base,"void")==0 && ptr_level==0) g_nodes[fn].type_is_void=1;
        parse_params(fn); expect(TK_RPAREN);
        if (cur_kind()==TK_SEMI) { advance(); g_nodes[fn].kind=NK_FUNC_PROTO; return fn; }
        node_add_child(fn, parse_block()); return fn;
    }

    /* global var */
    {
        int gn; int arr; gn=new_node(NK_GLOBAL_VAR);
        strcpy(g_nodes[gn].type_base,base);
        strcpy(g_nodes[gn].struct_name,stag);
        g_nodes[gn].type_ptr=ptr_level; g_nodes[gn].is_extern=is_ext;
        strcpy(g_nodes[gn].name,dname); arr=0;
        if (cur_kind()==TK_LBRACKET) {
            advance();
            if (cur_kind()==TK_INT_LIT) { arr=atoi(cur_val()); advance(); }
            expect(TK_RBRACKET);
        }
        g_nodes[gn].type_arr=arr;
        if (cur_kind()==TK_EQ) { advance(); node_add_child(gn,parse_expr()); }
        expect(TK_SEMI); return gn;
    }
}

int parse_program() {
    int prog; prog=new_node(NK_PROGRAM);
    while (cur_kind()!=TK_EOF) { node_add_child(prog,parse_top_level()); }
    return prog;
}

/* ── Code generation ─────────────────────────────────────────────────────── */

void *g_out;

void emit(char *s) { fprintf(g_out,"%s",s); }

void emit_type(int n, char *varname) {
    char *base; int j; char buf[32];
    base = g_nodes[n].type_base;
    if (strcmp(base,"struct")==0) { emit("struct "); emit(g_nodes[n].struct_name); }
    else { emit(base); }
    emit(" ");
    j=0; while(j<g_nodes[n].type_ptr){emit("*");j++;}
    if (varname!=(char*)0) emit(varname);
    if (g_nodes[n].type_arr>0) {
        emit("["); sprintf(buf,"%d",g_nodes[n].type_arr); emit(buf); emit("]");
    }
}

void emit_expr(int n) {
    int kind; char buf[64]; int cnt; int i;
    kind=g_nodes[n].kind;
    if (kind==NK_INT_LIT)  { sprintf(buf,"%d",g_nodes[n].ival); emit(buf); return; }
    if (kind==NK_CHAR_LIT) { sprintf(buf,"%d",g_nodes[n].ival); emit(buf); return; }
    if (kind==NK_STR_LIT)  { emit("\""); emit(g_nodes[n].name); emit("\""); return; }
    if (kind==NK_IDENT_REF){ emit(g_nodes[n].name); return; }
    if (kind==NK_ASSIGN) {
        emit_expr(node_get_child(n,0)); emit(" "); emit(g_nodes[n].name); emit(" ");
        emit_expr(node_get_child(n,1)); return;
    }
    if (kind==NK_BINOP) {
        emit("("); emit_expr(node_get_child(n,0)); emit(" "); emit(g_nodes[n].name); emit(" ");
        emit_expr(node_get_child(n,1)); emit(")"); return;
    }
    if (kind==NK_UNARY) {
        emit("("); emit(g_nodes[n].name); emit_expr(node_get_child(n,0)); emit(")"); return;
    }
    if (kind==NK_ADDR_OF) { emit("(&"); emit_expr(node_get_child(n,0)); emit(")"); return; }
    if (kind==NK_DEREF)   { emit("(*"); emit_expr(node_get_child(n,0)); emit(")"); return; }
    if (kind==NK_POSTFIX_INC) {
        emit("(");
        if (g_nodes[n].op_is_post==0) {
            if (g_nodes[n].op_sign==1) emit("++"); else emit("--");
            emit_expr(node_get_child(n,0));
        } else {
            emit_expr(node_get_child(n,0));
            if (g_nodes[n].op_sign==1) emit("++"); else emit("--");
        }
        emit(")"); return;
    }
    if (kind==NK_MEMBER) {
        emit_expr(node_get_child(n,0));
        if (g_nodes[n].is_arrow) emit("->"); else emit(".");
        emit(g_nodes[n].name); return;
    }
    if (kind==NK_INDEX) {
        emit_expr(node_get_child(n,0)); emit("["); emit_expr(node_get_child(n,1)); emit("]");
        return;
    }
    if (kind==NK_CALL) {
        int ci; int cc;
        cc=g_nodes[n].child_count; emit_expr(node_get_child(n,0)); emit("(");
        ci=1; while(ci<cc){ if(ci>1) emit(", "); emit_expr(node_get_child(n,ci)); ci++; }
        emit(")"); return;
    }
    if (kind==NK_CAST) {
        int j;
        emit("((");
        if (strcmp(g_nodes[n].type_base,"struct")==0) {
            emit("struct "); emit(g_nodes[n].struct_name);
        } else { emit(g_nodes[n].type_base); }
        j=0; while(j<g_nodes[n].type_ptr){emit("*");j++;}
        emit(")"); emit_expr(node_get_child(n,0)); emit(")"); return;
    }
    if (kind==NK_SIZEOF_TYPE) {
        int j;
        emit("sizeof(");
        if (strcmp(g_nodes[n].type_base,"struct")==0) {
            emit("struct "); emit(g_nodes[n].struct_name);
        } else { emit(g_nodes[n].type_base); }
        j=0; while(j<g_nodes[n].type_ptr){emit("*");j++;}
        emit(")"); return;
    }
    if (kind==NK_SIZEOF_EXPR) {
        emit("sizeof("); emit_expr(node_get_child(n,0)); emit(")"); return;
    }
    if (kind==NK_TERNARY) {
        emit("("); emit_expr(node_get_child(n,0)); emit(" ? ");
        emit_expr(node_get_child(n,1)); emit(" : ");
        emit_expr(node_get_child(n,2)); emit(")"); return;
    }
    sprintf(g_errbuf,"emit_expr: unknown kind %d\n",kind); cc_die();
}

void emit_stmt(int n) {
    int kind; kind=g_nodes[n].kind;
    if (kind==NK_NULL) return;
    if (kind==NK_BLOCK) {
        int cur; emit("{\n");
        cur=g_nodes[n].first_child;
        while (cur!=0) { emit_stmt(cur); cur=g_nodes[cur].next_sibling; }
        emit("}\n"); return;
    }
    if (kind==NK_VAR_DECL) {
        emit_type(n,g_nodes[n].name); emit(";\n");
        if (g_nodes[n].child_count>0) {
            emit(g_nodes[n].name); emit(" = "); emit_expr(node_get_child(n,0)); emit(";\n");
        }
        return;
    }
    if (kind==NK_RETURN) {
        emit("return");
        if (g_nodes[n].child_count>0) { emit(" "); emit_expr(node_get_child(n,0)); }
        emit(";\n"); return;
    }
    if (kind==NK_BREAK)    { emit("break;\n"); return; }
    if (kind==NK_CONTINUE) { emit("continue;\n"); return; }
    if (kind==NK_IF) {
        emit("if ("); emit_expr(node_get_child(n,0)); emit(") ");
        emit_stmt(node_get_child(n,1));
        if (g_nodes[n].child_count>2) { emit("else "); emit_stmt(node_get_child(n,2)); }
        return;
    }
    if (kind==NK_WHILE) {
        emit("while ("); emit_expr(node_get_child(n,0)); emit(") ");
        emit_stmt(node_get_child(n,1)); return;
    }
    if (kind==NK_FOR) {
        int init_n; int cond_n; int inc_n; int body_n; int ik;
        init_n=node_get_child(n,0); cond_n=node_get_child(n,1);
        inc_n =node_get_child(n,2); body_n=node_get_child(n,3);
        emit("for (");
        if (init_n!=0) {
            ik=g_nodes[init_n].kind;
            if (ik==NK_VAR_DECL) {
                emit_type(init_n,g_nodes[init_n].name);
                if (g_nodes[init_n].child_count>0) {
                    emit(" = "); emit_expr(node_get_child(init_n,0));
                }
            } else if (ik==NK_EXPR_STMT) {
                emit_expr(node_get_child(init_n,0));
            } else { emit_expr(init_n); }
        }
        emit("; ");
        if (cond_n!=0) emit_expr(cond_n);
        emit("; ");
        if (inc_n!=0) emit_expr(inc_n);
        emit(") "); emit_stmt(body_n); return;
    }
    if (kind==NK_EXPR_STMT) { emit_expr(node_get_child(n,0)); emit(";\n"); return; }
    sprintf(g_errbuf,"emit_stmt: unknown kind %d\n",kind); cc_die();
}

void emit_type_decl(int n) {
    int kind; int cnt; kind=g_nodes[n].kind; cnt=g_nodes[n].child_count;
    if (kind==NK_TYPEDEF_DECL) {
        if (cnt>0) {
            int cur;
            emit("typedef struct ");
            if (g_nodes[n].name[0]!=0) { emit(g_nodes[n].name); emit(" "); }
            emit("{\n");
            cur=g_nodes[n].first_child;
            while(cur!=0) {
                emit("    "); emit_type(cur,g_nodes[cur].name); emit(";\n");
                cur=g_nodes[cur].next_sibling;
            }
            emit("} "); emit(g_nodes[n].struct_name); emit(";\n\n");
        } else {
            char *base; base=g_nodes[n].type_base;
            emit("typedef ");
            if (strcmp(base,"struct")==0) {
                emit("struct "); emit(g_nodes[n].name);
            } else {
                emit(base);
                int j; j=0; while(j<g_nodes[n].type_ptr){emit("*");j++;}
            }
            emit(" "); emit(g_nodes[n].struct_name); emit(";\n\n");
        }
        return;
    }
    if (kind==NK_STRUCT_DECL) {
        int cur;
        emit("struct "); emit(g_nodes[n].name); emit(" {\n");
        cur=g_nodes[n].first_child;
        while(cur!=0) {
            emit("    "); emit_type(cur,g_nodes[cur].name); emit(";\n");
            cur=g_nodes[cur].next_sibling;
        }
        emit("};\n\n"); return;
    }
}

void emit_func_sig(int n) {
    int j; int param_cnt; int cur;
    if (strcmp(g_nodes[n].type_base,"struct")==0) {
        emit("struct "); emit(g_nodes[n].struct_name);
    } else { emit(g_nodes[n].type_base); }
    j=0; while(j<g_nodes[n].type_ptr){emit("*");j++;}
    emit(" "); emit(g_nodes[n].name); emit("(");
    /* params are all children except last (body) for FUNC_DECL */
    param_cnt=g_nodes[n].child_count;
    if (g_nodes[n].kind==NK_FUNC_DECL && param_cnt>0) param_cnt--;
    if (param_cnt==0 && !g_nodes[n].is_variadic) { emit("void"); }
    cur=g_nodes[n].first_child; j=0;
    while(j<param_cnt) {
        if (j>0) emit(", ");
        emit_type(cur,g_nodes[cur].name);
        cur=g_nodes[cur].next_sibling; j++;
    }
    if (g_nodes[n].is_variadic) { if(param_cnt>0) emit(", "); emit("..."); }
    emit(")");
}

void emit_program(int prog) {
    int cur; int n;
    fprintf(g_out,"/* Generated by C-Core-Compiler */\n\n");
    fprintf(g_out,"#include <stdio.h>\n");
    fprintf(g_out,"#include <stdlib.h>\n");
    fprintf(g_out,"#include <string.h>\n");
    fprintf(g_out,"#include <ctype.h>\n\n");

    /* pass 1: types */
    cur=g_nodes[prog].first_child;
    while(cur!=0) {
        if (g_nodes[cur].kind==NK_STRUCT_DECL||g_nodes[cur].kind==NK_TYPEDEF_DECL) {
            emit_type_decl(cur);
        }
        cur=g_nodes[cur].next_sibling;
    }

    /* pass 2: global vars */
    cur=g_nodes[prog].first_child;
    while(cur!=0) {
        if (g_nodes[cur].kind==NK_GLOBAL_VAR) {
            if (g_nodes[cur].is_extern) emit("extern ");
            emit_type(cur,g_nodes[cur].name);
            if (g_nodes[cur].child_count>0) {
                emit(" = "); emit_expr(node_get_child(cur,0));
            }
            emit(";\n");
        }
        cur=g_nodes[cur].next_sibling;
    }
    emit("\n");

    /* pass 3: non-extern function prototypes only
       (extern ones are covered by the included headers above) */
    cur=g_nodes[prog].first_child;
    while(cur!=0) {
        if (g_nodes[cur].kind==NK_FUNC_PROTO && !g_nodes[cur].is_extern) {
            emit_func_sig(cur); emit(";\n");
        }
        cur=g_nodes[cur].next_sibling;
    }

    /* pass 4: forward-declare defined functions */
    cur=g_nodes[prog].first_child;
    while(cur!=0) {
        if (g_nodes[cur].kind==NK_FUNC_DECL) {
            emit_func_sig(cur); emit(";\n");
        }
        cur=g_nodes[cur].next_sibling;
    }
    emit("\n");

    /* pass 5: function bodies */
    cur=g_nodes[prog].first_child;
    while(cur!=0) {
        n=cur;
        if (g_nodes[n].kind==NK_FUNC_DECL) {
            int body_n;
            emit_func_sig(n); emit(" ");
            body_n=node_get_child(n,g_nodes[n].child_count-1);
            emit_stmt(body_n); emit("\n");
        }
        cur=g_nodes[cur].next_sibling;
    }
}

/* ── main ────────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[]) {
    char *src_path; char *out_path;
    void *fp; int src_len; char *src;
    char cmd[1024]; char tmp_c[256];
    int prog; int i;

    init_token_kinds(); init_node_kinds(); init_keywords(); init_nodes();
    g_mem_top=0; g_tok_count=0; g_typedef_count=0; g_cur=0;

    src_path=(char*)0; out_path=(char*)0;
    i=1;
    while(i<argc) {
        if (strcmp(argv[i],"-o")==0 && i+1<argc) { out_path=argv[i+1]; i+=2; }
        else { src_path=argv[i]; i++; }
    }
    if (src_path==(char*)0) { write(2,"Usage: compiler <src.c> [-o out]\n",33); exit(1); }
    if (out_path==(char*)0) out_path="a.out";

    fp=fopen(src_path,"r");
    if (fp==(void*)0) { sprintf(g_errbuf,"Cannot open: %s\n",src_path); cc_die(); }
    fseek(fp,0,2); src_len=ftell(fp); fseek(fp,0,0);
    src=(char*)arena_alloc(src_len+1);
    fread((void*)src,1,src_len,fp); src[src_len]=0; fclose(fp);

    tokenize(src,src_len);
    prog=parse_program();

    strcpy(tmp_c,"/tmp/_cc_generated.c");
    g_out=fopen(tmp_c,"w");
    if (g_out==(void*)0) { write(2,"Cannot open temp file\n",22); exit(1); }
    emit_program(prog); fclose(g_out);

    sprintf(cmd,"clang -Wno-implicit-function-declaration -o %s %s",out_path,tmp_c);
    if (system(cmd)!=0) { write(2,"clang failed\n",13); exit(1); }
    return 0;
}
