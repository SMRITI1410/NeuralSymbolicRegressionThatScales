import numpy as np
import multiprocessing
from multiprocessing import Manager
import click
import warnings
from tqdm import tqdm
import os
from nesymres.dataset import generator
import numexpr
import time
import signal
from nesymres import utils, dclasses

def handler(signum, frame):
    raise TimeoutError

class Pipepile:
    def __init__(self, env: generator.Generator):
        self.env = env
        manager = Manager()
        self.cnt = manager.list()

    def return_training_set(self, i):
        np.random.seed(i)
        while True:
            res = self.create_lambda(np.random.randint(2**32-1))
            try:
                if len(res) > 2:
                    return res
            except TimeoutError:
                continue
        return ["Loop terminated", i]

    def create_lambda(self, i):
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(1)
        try:
            prefix_not, expression = self.env.generate_equation(np.random)
            if expression == "0" or type(expression) == str:
                signal.alarm(0)
                raise ArithmeticError

            sy = expression.free_symbols
            sy_str = {str(s) for s in sy}
            if not frozenset(sy_str) in set(
                [frozenset(self.env.variables[: idx + 1]) for idx in range(3)]
            ):
                signal.alarm(0)
                return ["Variable order not consistent", i]

            sy = set(map(str, sy))
            format_string, _ = self.env._prefix_to_infix_with_constants(prefix_not)
            n_const = self.env.count_number_of_constants(format_string)
            consts = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"]
            constants_expression = format_string.format(*tuple(consts[:n_const]))
            if time.time() - s > 0.02:
                signal.alarm(0)
                return ["Too much time", i]
            a = lambdify(
                "x,y,z" + "," + ",".join(consts),
                constants_expression,
                modules=["numpy"],
            )

            res = [a.__code__, str(expression), format_string, sy, i]
            signal.alarm(0)
        except:
            res = ["TimeOut Error", i]
            signal.alarm(0)
        return res


@click.command()
@click.option(
    "--number_of_equations",
    default=5000000,
    help="Total number of equations to generate",
)
@click.option("--multi/--no-multi", default=True)
@click.option("--debug/--no-debug", default=False)
def creator(number_of_equations, debug):
    total_number = number_of_equations
    warnings.filterwarnings("error")
    with open("config.json") as f:
        d = json.load(f)
        env = utils.create_env(d)

    env_pip = pipeline.Pipepile(env)
    starttime = time.time()
    func = []
    res = []
    counter = []
    if debug:
        try:
            with Pool(multiprocessing.cpu_count()) as p:
                max_ = total_number
                with tqdm(total=max_) as pbar:
                    for f in p.imap_unordered(
                        env_pip.return_training_set, range(0, total_number)
                    ):
                        pbar.update()
                        res.append(f)
        except:
            pass

    else:
        res = map(env_pip.return_validation_set, tqdm(range(0, total_number)))

    funcs = [l[0] for l in res if len(l) > 2]
    no_c = [l[1] for l in res if len(l) > 2]
    w_c = [l[2] for l in res if len(l) > 2]
    pref = [l[3] for l in res if len(l) > 2]
    syy = [l[4] for l in res if len(l) > 2]
    errors = [[l[0], l[1]] for l in res if len(l) == 2]
    print("Expression generation took {} seconds".format(time.time() - starttime))
    print(
        "Percentage of errors during expression generation {}".format(
            len(errors) / total_number
        )
    )
    starttime = time.time()
    cntn = 0
    fin_no_c = []
    fin_funcs = []
    fin_syy = []
    fin_toks = []
    fin_return_home = []
    fin_w_c = []
    for e in range(len(pref) - 1):
        try:
            token_sentence = env.tokenize(pref[e])
        except Exception as l:
            cntn += 1
            continue
        fin_toks.append(token_sentence)
        fin_return_home.append(
            env._prefix_to_infix_benchmark(env.de_tokenize(token_sentence[1:]))
        )
        fin_no_c.append(no_c[e])
        fin_funcs.append(funcs[e])
        fin_syy.append(syy[e])
        fin_w_c.append(w_c[e])

    print("Tokenization took {} seconds".format(time.time() - starttime))
    print("Percentage of errors during tokenization {}".format(cntn / total_number))
    d = {
        "Expression": fin_no_c,
        "Format_Expression": fin_w_c,
        "Tokenized": fin_toks,
        "Symbol": fin_syy,
        "Funcs": fin_funcs,
        "Return": fin_return_home,
        "Config": d,
    }
    if not debug:
        folder = "data/facebook/"
    else:
        folder = "data/facebook/debug"
    file_name = "{}K".format(int(number_of_equations / 1000))
    path = os.path.join(folder, file_name)
    with open(path, "wb") as file:
        pickle.dump(d, file)

if __name__ == "__main__":
    creator()